from datetime import timedelta

import pytest

from app.api import routes
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.database import Scan, StudentProfile, utcnow
from app.services.auth import create_session
from app.api.routes import discover_registration_state


def eligible_student(user_id: int, login: str) -> dict:
    return {"id": user_id, "login": login, "display_name": login.title(), "image_url": None,
            "campus": "Paris", "promotion": "2024", "level": 5.0, "project_status": "in_progress",
            "team_status": "registered_without_team", "profile_url": "https://profile.intra.42.fr",
            "classification_reason": "verified", "available_data": {"project_user": {"status": "searching_a_group", "locked?": False}}}


def test_discover_registration_state_keeps_eligibility_separate_from_enrollment():
    assert discover_registration_state({"status": "searching_a_group"}) == "subscribed"
    assert discover_registration_state({"status": "in_progress"}) == "subscribed"
    assert discover_registration_state({"status": "available", "locked?": False}) is None
    assert discover_registration_state({"status": "available", "locked?": True}) is None
    assert discover_registration_state({"status": "finished", "validated?": True}) is None


@pytest.mark.asyncio
async def test_project_picker_uses_only_documented_registration_eligibility(client, monkeypatch):
    settings = get_settings()
    previous_demo_mode = settings.demo_mode
    settings.demo_mode = False
    group_session = {"id": 1, "campus_id": 9, "cursus_id": 21, "solo": False, "max_people": 5}
    solo_session = {"id": 2, "campus_id": 9, "cursus_id": 21, "solo": True, "max_people": 1}
    calls: list[str] = []

    class FakeClient:
        def __init__(self, _settings):
            pass

        async def get_all(self, path, **_kwargs):
            calls.append(path)
            return [{
                "project": {"id": 10, "name": "Subscribed", "slug": "subscribed",
                            "project_sessions": [group_session]},
                "status": "in_progress",
            }]

        async def get_allowed_registration_projects(self, user_id):
            calls.append(f"/users/{user_id}/projects_users/registration")
            return [
                {"id": 20, "name": "Actually eligible", "slug": "actually-eligible",
                 "project_sessions": [group_session]},
                {"id": 30, "name": "Eligible solo", "slug": "eligible-solo",
                 "project_sessions": [solo_session]},
            ]

        async def close(self):
            pass

    monkeypatch.setattr(routes, "FortyTwoClient", FakeClient)
    try:
        async with SessionLocal() as session:
            token = await create_session(session, settings, {
                "id": 1337,
                "login": "eligible",
                "usual_full_name": "Eligible Student",
                "campus": [{"id": 9, "name": "Paris"}],
                "cursus_users": [{"id": 1, "level": 5.0}],
            })
        client.cookies.set("team_finder_session", token)
        response = await client.get("/api/discover/projects")
        assert response.status_code == 200
        assert [(item["id"], item["subscription_status"]) for item in response.json()["items"]] == [
            (10, "subscribed"),
            (20, "eligible"),
        ]
        assert calls == ["/projects_users", "/users/1337/projects_users/registration"]
    finally:
        settings.demo_mode = previous_demo_mode


@pytest.mark.asyncio
async def test_project_scoped_mutual_swipes_create_one_match(client):
    async with SessionLocal() as session:
        first = await create_session(session, get_settings(), {"id": 1, "login": "ada", "usual_full_name": "Ada", "cursus_users": []})
        second = await create_session(session, get_settings(), {"id": 2, "login": "lin", "usual_full_name": "Lin", "cursus_users": []})
        # create_session tolerates sparse test profiles; give the peer a campus
        peer = await session.get(StudentProfile, 2); peer.campus_id = 9; peer.campus_name = "Paris"
        actor = await session.get(StudentProfile, 1); actor.campus_id = 9; actor.campus_name = "Paris"
        session.add(Scan(id="match-scan", status="completed", progress_stage="Done", completed_work=1, total_work=1,
            source="demo", created_at=utcnow(), started_at=utcnow(), completed_at=utcnow(), data_retrieved_at=utcnow(),
            configuration={"project_id": 101, "project_name": "minishell", "campus_id": 9, "max_team_size": 2},
            result={"students": [eligible_student(1, "ada"), eligible_student(2, "lin")], "teams": [], "summary": {}}))
        await session.commit()

    client.cookies.set("team_finder_session", first)
    projects = await client.get("/api/discover/projects")
    assert projects.status_code == 200 and projects.json()["items"][0]["id"] == 101
    assert projects.json()["items"][0]["subscription_status"] == "subscribed"
    candidates = await client.get("/api/discover/candidates?project_id=101")
    assert candidates.status_code == 200 and candidates.json()["items"][0]["login"] == "lin"
    assert (await client.post("/api/swipes", json={"target_user_id": 2, "project_id": 101, "direction": "right"})).json()["matched"] is False

    client.cookies.set("team_finder_session", second)
    response = await client.post("/api/swipes", json={"target_user_id": 1, "project_id": 101, "direction": "right"})
    assert response.status_code == 200 and response.json()["matched"] is True
    # Retrying the same intent must not create a second match.
    assert (await client.post("/api/swipes", json={"target_user_id": 1, "project_id": 101, "direction": "right"})).json()["match_id"] == response.json()["match_id"]
