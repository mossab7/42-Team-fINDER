import pytest

from app.api import routes
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.auth import OAUTH_STATE_COOKIE, SESSION_COOKIE, authorization_url, create_session
from app.services.auth import AUTHORIZED_PROJECTS_CACHE
from app.repositories.cache import CacheRepository


def test_authorization_url_has_state_and_documented_callback():
    settings = get_settings()
    url = authorization_url(settings, "csrf-state")
    assert "oauth/authorize" in url
    assert "response_type=code" in url
    assert "state=csrf-state" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fapi%2Fauth%2Fcallback" in url


@pytest.mark.asyncio
async def test_auth_status_and_revocable_session(client):
    anonymous = await client.get("/api/auth/me")
    assert anonymous.status_code == 200
    assert anonymous.json()["authenticated"] is False
    settings = get_settings()
    async with SessionLocal() as session:
        token = await create_session(session, settings, {
            "id": 42, "login": "cadet", "usual_full_name": "Cadet 42",
            "_authorized_projects": [{"id": 101, "name": "webserv", "slug": "webserv", "extra": "discarded"}],
        })
        catalog = await CacheRepository(session, settings.session_ttl_hours * 3600).get(
            AUTHORIZED_PROJECTS_CACHE, "42"
        )
        assert catalog and catalog[0] == [{"id": 101, "name": "webserv", "slug": "webserv", "project_sessions": None}]
    client.cookies.set(SESSION_COOKIE, token)
    authenticated = await client.get("/api/auth/me")
    assert authenticated.json()["authenticated"] is True
    assert authenticated.json()["user"]["login"] == "cadet"
    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert (await client.get("/api/auth/me")).json()["authenticated"] is False


@pytest.mark.asyncio
async def test_callback_rejects_invalid_csrf_state(client):
    response = await client.get("/api/auth/callback?code=never-used&state=incorrect", follow_redirects=False)
    assert response.status_code == 302
    assert "auth=failed" in response.headers["location"]


@pytest.mark.asyncio
async def test_required_mode_blocks_data_but_accepts_42_callback(client, monkeypatch):
    settings = get_settings()
    previous = settings.auth_required
    settings.auth_required = True

    async def profile(*_args, **_kwargs):
        return {"id": 84, "login": "student", "usual_full_name": "Student 42", "cursus_users": [{"id": 1}]}

    monkeypatch.setattr(routes, "exchange_code", profile)
    try:
        assert (await client.get("/api/campuses")).status_code == 401
        client.cookies.set(OAUTH_STATE_COOKIE, "correct")
        callback = await client.get("/api/auth/callback?code=code&state=correct", follow_redirects=False)
        assert callback.status_code == 302
        assert "team_finder_session=" in callback.headers["set-cookie"]
        assert (await client.get("/api/campuses")).status_code == 200
    finally:
        settings.auth_required = previous
