from app.services.project_configuration import derive_project_configuration, select_project_session


def test_selects_exact_campus_cursus_session():
    project = {"project_sessions": [
        {"id": 1, "campus_id": 2, "cursus_id": 21},
        {"id": 2, "campus_id": 1, "cursus_id": 21},
    ]}
    assert select_project_session(project, 1)["id"] == 2


def test_derives_official_group_range_and_solo_defaults():
    group = derive_project_configuration({
        "id": 10,
        "campus_id": 1,
        "solo": False,
        "project_sessions_rules": [{
            "rule": {"internal_name": "GroupSizeBetweenNAndM"},
            "params": [{"value": "4"}, {"value": "5"}],
        }],
    })
    assert group["min_team_size"] == 4
    assert group["max_team_size"] == 5
    assert group["maximum_source"] == "group_rule"
    solo = derive_project_configuration({"id": 11, "campus_id": 1, "solo": True})
    assert solo["solo"] is True
    assert solo["max_team_size"] == 1
