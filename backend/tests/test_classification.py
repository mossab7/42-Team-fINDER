from datetime import date, datetime, timezone

from app.schemas.scan import PromotionDefinition, ScanCreate
from app.services.classification import classify, matches_promotion, reached_black_hole
from app.services.fixtures import fixture_data
from app.services.scanner import users_from_cursus_users


def configuration(include_unavailable=False):
    return ScanCreate(campus_id=1, campus_name="Paris", project_id=101, project_name="ft_transcendence", promotion=PromotionDefinition(type="cursus_year", year=2024), max_team_size=5, include_unavailable=include_unavailable)


def test_cursus_and_piscine_promotion_filtering():
    users, _, _ = fixture_data()
    assert matches_promotion(users[0], PromotionDefinition(type="cursus_year", year=2024))
    assert matches_promotion(users[0], PromotionDefinition(type="piscine", year=2024, month=9))
    assert matches_promotion(users[0], PromotionDefinition(type="date_range", start_date=date(2024, 9, 1), end_date=date(2024, 9, 30)))
    assert not matches_promotion(users[2], PromotionDefinition(type="piscine", year=2024, month=9))


def test_cursus_index_records_are_shaped_for_promotion_classification():
    records = [{
        "id": 9, "begin_at": "2024-11-13T11:14:00.000Z", "level": 9.49,
        "cursus_id": 21, "user": {"id": 42, "login": "student"},
    }]
    users = users_from_cursus_users(records)
    assert users[0]["id"] == 42
    assert users[0]["cursus_users"][0]["begin_at"].startswith("2024-")
    assert matches_promotion(users[0], PromotionDefinition(type="cursus_year", year=2024))


def test_classifies_students_and_full_external_membership():
    users, project_users, teams = fixture_data()
    students, team_results, summary = classify(configuration(), users, project_users, teams)
    statuses = {item.login: item.team_status for item in students}
    assert statuses == {"ada": "searching_group", "grace": "not_registered"}
    assert team_results[0].member_count == 2
    assert {member.login for member in team_results[0].members} == {"linus", "katherine"}
    assert summary["total_eligible_students"] == 5
    assert summary["students_without_active_teams"] == 2
    assert summary["potentially_available_spots"] == 7


def test_incomplete_team_data_is_uncertain_not_no_team():
    users, project_users, _ = fixture_data()
    students, _, summary = classify(configuration(), users, project_users, [], teams_complete=False)
    assert all(item.team_status == "uncertain" for item in students if item.login != "alan")
    assert summary["students_without_active_teams"] == 0


def test_completed_and_unavailable_hidden_by_default():
    users, project_users, teams = fixture_data()
    students, team_results, _ = classify(configuration(), users, project_users, teams)
    assert "alan" not in {item.login for item in students}
    assert 303 not in {item.id for item in team_results}
    students, team_results, _ = classify(configuration(True), users, project_users, teams)
    assert "alan" in {item.login for item in students}
    assert 303 in {item.id for item in team_results}


def test_locked_team_is_capacity_not_confirmed_joinable():
    users, project_users, teams = fixture_data()
    _, team_results, _ = classify(configuration(), users, project_users, teams)
    assert {item.availability for item in team_results} == {"potential_capacity"}


def test_teams_at_selected_size_limit_are_hidden_by_default():
    users, project_users, teams = fixture_data()
    config = configuration()
    config.max_team_size = 2
    _, team_results, _ = classify(config, users, project_users, teams)
    assert {item.id for item in team_results} == {302}
    config.include_unavailable = True
    _, team_results, _ = classify(config, users, project_users, teams)
    assert {item.id for item in team_results} == {301, 302, 303}


def test_students_past_black_hole_are_excluded_from_peer_results():
    users, project_users, teams = fixture_data()
    users[0]["cursus_users"][0]["blackholed_at"] = "2000-01-01T00:00:00Z"
    users[0]["cursus_users"][0]["end_at"] = "2000-01-01T12:00:00Z"
    assert reached_black_hole(users[0])
    students, _, summary = classify(configuration(), users, project_users, teams)
    assert "ada" not in {item.login for item in students}
    assert summary["total_eligible_students"] == 4
    assert summary["excluded_blackholed_students"] == 1


def test_past_black_hole_deadline_excludes_even_when_cursus_end_is_null():
    users, project_users, teams = fixture_data()
    users[0]["cursus_users"][0]["blackholed_at"] = "2000-01-01T00:00:00Z"
    users[0]["cursus_users"][0]["end_at"] = None
    assert reached_black_hole(users[0])
    students, _, summary = classify(configuration(), users, project_users, teams)
    assert "ada" not in {item.login for item in students}
    assert summary["total_eligible_students"] == 4
    assert summary["excluded_blackholed_students"] == 1


def test_future_black_hole_deadline_is_not_excluded():
    users, project_users, teams = fixture_data()
    users[0]["cursus_users"][0]["blackholed_at"] = "2999-01-01T00:00:00Z"
    users[0]["cursus_users"][0]["end_at"] = None
    assert not reached_black_hole(users[0])
    students, _, summary = classify(configuration(), users, project_users, teams)
    assert "ada" in {item.login for item in students}
    assert summary["excluded_blackholed_students"] == 0


def test_transcender_is_not_excluded_by_a_stale_black_hole_timestamp():
    users, project_users, teams = fixture_data()
    cursus = users[0]["cursus_users"][0]
    cursus.update({"blackholed_at": "2000-01-01T00:00:00Z", "end_at": None, "grade": "Transcender"})
    assert not reached_black_hole(users[0])
    students, _, summary = classify(configuration(), users, project_users, teams)
    assert "ada" in {item.login for item in students}
    assert summary["excluded_blackholed_students"] == 0


def test_main_cursus_black_hole_is_not_hidden_by_active_piscine_record():
    users, _, _ = fixture_data()
    users[0]["cursus_users"][0].update({
        "cursus_id": 21, "blackholed_at": "2000-01-01T00:00:00Z", "end_at": None,
    })
    users[0]["cursus_users"].append({
        "cursus_id": 1, "begin_at": "2999-01-01T00:00:00Z", "end_at": None,
        "blackholed_at": None, "grade": "Pisciner",
    })
    assert reached_black_hole(users[0])


def test_ended_cursus_without_matching_black_hole_time_is_not_inferred():
    user = {
        "id": 9,
        "cursus_users": [{
            "begin_at": "2024-01-01T00:00:00Z",
            "blackholed_at": "2024-12-01T00:00:00Z",
            "end_at": "2024-06-01T00:00:00Z",
        }],
    }
    assert not reached_black_hole(user, now=datetime(2025, 1, 1, tzinfo=timezone.utc))


def test_solo_project_lists_active_registrations_without_team_cards():
    users, project_users, teams = fixture_data()
    config = configuration()
    config.project_solo = True
    config.max_team_size = 1
    students, team_results, summary = classify(config, users, project_users, teams)
    assert {item.login for item in students} == {"ada", "linus", "margaret"}
    assert all(item.team_status == "working_solo" for item in students)
    assert team_results == []
    assert summary["students_working_on_project"] == 3
