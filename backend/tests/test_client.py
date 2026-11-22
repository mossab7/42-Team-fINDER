import httpx
import pytest

from app.core.config import Settings
from app.services.fortytwo import FortyTwoClient, deduplicate


@pytest.mark.asyncio
async def test_token_reuse_and_complete_pagination():
    calls = {"token": 0, "pages": 0}
    async def handler(request: httpx.Request):
        if request.url.path == "/oauth/token":
            calls["token"] += 1
            return httpx.Response(200, json={"access_token": "ok", "expires_in": 7200})
        calls["pages"] += 1
        page = int(request.url.params["page[number]"])
        return httpx.Response(200, json=([{"id": i} for i in range(100)] if page == 1 else [{"id": 101}]))
    settings = Settings(ft_client_id="id", ft_client_secret="secret", ft_api_base_url="https://example.test", ft_token_url="https://example.test/oauth/token")
    client = FortyTwoClient(settings, transport=httpx.MockTransport(handler))
    assert len(await client.get_all("/items")) == 101
    assert calls == {"token": 1, "pages": 2}
    await client.close()


@pytest.mark.asyncio
async def test_header_pagination_fetches_all_remaining_pages():
    pages: list[int] = []

    async def handler(request: httpx.Request):
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "ok", "expires_in": 7200})
        page = int(request.url.params["page[number]"])
        pages.append(page)
        payload = [{"id": page * 100 + index} for index in range(100 if page < 3 else 1)]
        return httpx.Response(
            200,
            json=payload,
            headers={"X-Total": "201", "X-Per-Page": "100"},
        )

    settings = Settings(
        ft_client_id="id",
        ft_client_secret="secret",
        ft_api_base_url="https://x.test",
        ft_token_url="https://x.test/oauth/token",
    )
    client = FortyTwoClient(settings, transport=httpx.MockTransport(handler))
    assert len(await client.get_all("/items")) == 201
    assert sorted(pages) == [1, 2, 3]
    await client.close()


@pytest.mark.asyncio
async def test_rate_limit_retries(monkeypatch):
    calls = 0
    async def handler(request: httpx.Request):
        nonlocal calls
        if request.url.path == "/oauth/token": return httpx.Response(200, json={"access_token":"ok","expires_in":7200})
        calls += 1
        return httpx.Response(429, headers={"Retry-After":"0"}) if calls == 1 else httpx.Response(200, json=[])
    settings=Settings(ft_client_id="id",ft_client_secret="secret",ft_api_base_url="https://x.test",ft_token_url="https://x.test/oauth/token")
    client=FortyTwoClient(settings,transport=httpx.MockTransport(handler))
    assert await client.get_all("/items") == []
    assert calls == 2
    await client.close()


@pytest.mark.asyncio
async def test_token_rate_limit_is_retried(monkeypatch):
    token_calls = 0

    async def handler(request: httpx.Request):
        nonlocal token_calls
        if request.url.path == "/oauth/token":
            token_calls += 1
            if token_calls == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200, json={"access_token": "ok", "expires_in": 7200})
        return httpx.Response(200, json=[])

    settings = Settings(
        ft_client_id="id", ft_client_secret="secret",
        ft_api_base_url="https://x.test", ft_token_url="https://x.test/oauth/token",
        api_min_interval_seconds=0,
    )
    client = FortyTwoClient(settings, transport=httpx.MockTransport(handler))
    assert await client.get_all("/items") == []
    assert token_calls == 2
    await client.close()


@pytest.mark.asyncio
async def test_rate_limit_without_retry_after_uses_long_backoff(monkeypatch):
    calls = 0
    sleeps: list[float] = []

    async def handler(request: httpx.Request):
        nonlocal calls
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "ok", "expires_in": 7200})
        calls += 1
        return httpx.Response(429) if calls == 1 else httpx.Response(200, json=[])

    async def fake_sleep(delay: float):
        sleeps.append(delay)

    monkeypatch.setattr("app.services.fortytwo.asyncio.sleep", fake_sleep)
    settings = Settings(
        ft_client_id="id", ft_client_secret="secret",
        ft_api_base_url="https://x.test", ft_token_url="https://x.test/oauth/token",
        api_min_interval_seconds=0,
    )
    client = FortyTwoClient(settings, transport=httpx.MockTransport(handler))
    assert await client.get_all("/items") == []
    assert calls == 2
    assert sleeps and sleeps[0] >= 5
    await client.close()


@pytest.mark.asyncio
async def test_project_teams_uses_filterable_teams_index():
    observed: dict[str, str] = {}

    async def handler(request: httpx.Request):
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "ok", "expires_in": 7200})
        observed["path"] = request.url.path
        observed["project_id"] = request.url.params["filter[project_id]"]
        return httpx.Response(200, json=[])

    settings = Settings(
        ft_client_id="id",
        ft_client_secret="secret",
        ft_api_base_url="https://x.test",
        ft_token_url="https://x.test/oauth/token",
    )
    client = FortyTwoClient(settings, transport=httpx.MockTransport(handler))
    assert await client.get_project_teams(1337) == []
    assert observed == {"path": "/teams", "project_id": "1337"}
    await client.close()


@pytest.mark.asyncio
async def test_cohort_registration_and_team_bulk_filters():
    requests: list[tuple[str, str, str]] = []

    async def handler(request: httpx.Request):
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "ok", "expires_in": 7200})
        requests.append((
            request.url.path,
            request.url.params.get("filter[project_id]", ""),
            request.url.params.get("filter[user_id]", request.url.params.get("filter[id]", "")),
        ))
        return httpx.Response(200, json=[])

    settings = Settings(
        ft_client_id="id",
        ft_client_secret="secret",
        ft_api_base_url="https://x.test",
        ft_token_url="https://x.test/oauth/token",
    )
    client = FortyTwoClient(settings, transport=httpx.MockTransport(handler))
    assert await client.get_project_users(1337, [11, 12]) == []
    assert await client.get_teams_by_ids([21, 22]) == []
    assert requests == [
        ("/projects_users", "1337", "11,12"),
        ("/teams", "", "21,22"),
    ]
    await client.close()


@pytest.mark.asyncio
async def test_cursus_users_are_filtered_by_campus_cursus_and_enrollment_window():
    observed: dict[str, str] = {}

    async def handler(request: httpx.Request):
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "ok", "expires_in": 7200})
        observed.update({key: value for key, value in request.url.params.items()})
        return httpx.Response(200, json=[])

    settings = Settings(
        ft_client_id="id", ft_client_secret="secret",
        ft_api_base_url="https://x.test", ft_token_url="https://x.test/oauth/token",
    )
    client = FortyTwoClient(settings, transport=httpx.MockTransport(handler))
    assert await client.get_campus_cursus_users(21, "2024-01-01", "2024-12-31") == []
    assert observed["filter[campus_id]"] == "21"
    assert observed["filter[cursus_id]"] == "21"
    assert observed["range[begin_at]"] == "2024-01-01T00:00:00Z,2024-12-31T23:59:59Z"
    await client.close()


def test_duplicate_records_keep_latest():
    assert deduplicate([{"id":1,"v":"a"},{"id":1,"v":"b"}]) == [{"id":1,"v":"b"}]
