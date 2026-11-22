import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.core.config import Settings


class FortyTwoAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class FortyTwoClient:
    """Async client for documented 42 endpoints with renewable client credentials."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.ft_api_base_url,
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            transport=transport,
        )
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(settings.api_concurrency)
        self._rate_lock = asyncio.Lock()
        self._next_request_at = 0.0

    async def close(self) -> None:
        await self._client.aclose()

    async def _get_token(self, *, force: bool = False) -> str:
        if not force and self._token and time.monotonic() < self._token_expires_at - 30:
            return self._token
        async with self._token_lock:
            if not force and self._token and time.monotonic() < self._token_expires_at - 30:
                return self._token
            if not self.settings.ft_client_id or not self.settings.ft_client_secret:
                raise FortyTwoAPIError("42 API credentials are not configured")
            try:
                for attempt in range(self.settings.max_retries + 1):
                    response = await self._client.post(
                        self.settings.ft_token_url,
                        data={
                            "grant_type": "client_credentials",
                            "client_id": self.settings.ft_client_id,
                            "client_secret": self.settings.ft_client_secret,
                        },
                    )
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < self.settings.max_retries:
                            await asyncio.sleep(self._retry_delay(response, attempt))
                            continue
                    response.raise_for_status()
                    payload = response.json()
                    self._token = payload["access_token"]
                    self._token_expires_at = time.monotonic() + int(payload.get("expires_in", 7200))
                    return self._token
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise FortyTwoAPIError("Unable to authenticate with the 42 API") from exc
            raise FortyTwoAPIError("Unable to authenticate with the 42 API")

    @staticmethod
    def _retry_delay(response: httpx.Response | None, attempt: int) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), 30.0)
                except ValueError:
                    pass
            # The API's spam limiter does not always include Retry-After.
            # A longer fallback prevents immediate retries from extending the
            # temporary block.
            if response.status_code == 429:
                return min((5 * (2**attempt)) + random.uniform(0, 0.25), 30.0)
        return min((2**attempt) + random.uniform(0, 0.25), 12.0)

    async def _wait_for_request_slot(self) -> None:
        """Pace all API calls from this client to avoid 42's burst limiter."""
        async with self._rate_lock:
            now = time.monotonic()
            delay = self._next_request_at - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._next_request_at = time.monotonic() + self.settings.api_min_interval_seconds

    async def _apply_shared_cooldown(self, delay: float) -> None:
        """Make concurrently queued requests respect a rate-limit response."""
        async with self._rate_lock:
            self._next_request_at = max(self._next_request_at, time.monotonic() + delay)

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        unauthorized_retried = False
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            token = await self._get_token(force=unauthorized_retried)
            try:
                async with self._semaphore:
                    await self._wait_for_request_slot()
                    response = await self._client.request(
                        method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs
                    )
                if response.status_code == 401 and not unauthorized_retried:
                    unauthorized_retried = True
                    self._token = None
                    continue
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.settings.max_retries:
                        delay = self._retry_delay(response, attempt)
                        if response.status_code == 429:
                            await self._apply_shared_cooldown(delay)
                        else:
                            await asyncio.sleep(delay)
                        continue
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < self.settings.max_retries:
                    await asyncio.sleep(self._retry_delay(None, attempt))
                    continue
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    raise FortyTwoAPIError(
                        "The 42 API rate limit is still active after bounded retries. "
                        "Please wait a minute and try again; completed cache data will be reused.",
                        status_code=429,
                    ) from exc
                detail = exc.response.text[:300]
                raise FortyTwoAPIError(
                    f"42 API returned {exc.response.status_code}: {detail}",
                    status_code=exc.response.status_code,
                ) from exc
        raise FortyTwoAPIError("42 API request failed after bounded retries") from last_error

    async def get_all(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        page_size: int = 100,
        progress: Callable[[int], Awaitable[None]] | None = None,
    ) -> list[dict[str, Any]]:
        async def fetch_page(page: int) -> tuple[list[dict[str, Any]], httpx.Headers]:
            page_params = dict(params or {})
            page_params.update({"page[number]": page, "page[size]": page_size})
            response = await self.request("GET", path, params=page_params)
            payload = response.json()
            if not isinstance(payload, list):
                raise FortyTwoAPIError(f"Unexpected response shape for {path}")
            if progress:
                await progress(len(payload))
            return payload, response.headers

        first_page, headers = await fetch_page(1)
        total_header = headers.get("X-Total")
        per_page_header = headers.get("X-Per-Page")
        if total_header and per_page_header:
            try:
                total = int(total_header)
                per_page = int(per_page_header)
            except ValueError:
                total = per_page = 0
            if total > len(first_page) and per_page > 0:
                page_count = (total + per_page - 1) // per_page
                remaining = await asyncio.gather(
                    *(fetch_page(page) for page in range(2, page_count + 1))
                )
                return first_page + [item for payload, _ in remaining for item in payload]
            if total <= len(first_page):
                return first_page

        # Some test doubles and API responses omit pagination headers. Keep a
        # safe sequential fallback that stops on the first short page.
        result = list(first_page)
        page = 1
        payload = first_page
        while len(payload) == page_size:
            page += 1
            payload, _ = await fetch_page(page)
            result.extend(payload)
        return result

    async def get_project_teams(self, project_id: int) -> list[dict[str, Any]]:
        """Return teams for a project via the documented filterable index."""
        return await self.get_all("/teams", params={"filter[project_id]": project_id})

    async def get_project_users(
        self, project_id: int, user_ids: list[int], *, batch_size: int = 75
    ) -> list[dict[str, Any]]:
        """Return project registrations only for the selected cohort."""
        if not user_ids:
            return []
        batches = [user_ids[index:index + batch_size] for index in range(0, len(user_ids), batch_size)]
        results = await asyncio.gather(*(
            self.get_all(
                "/projects_users",
                params={
                    "filter[project_id]": project_id,
                    "filter[user_id]": ",".join(map(str, batch)),
                },
            )
            for batch in batches
        ))
        return [item for result in results for item in result]

    async def get_campus_cursus_users(
        self, campus_id: int, begin_at: str, end_at: str, *, cursus_id: int = 21
    ) -> list[dict[str, Any]]:
        """Return 42cursus enrollments for one campus and enrollment window."""
        return await self.get_all(
            "/cursus_users",
            params={
                "filter[campus_id]": campus_id,
                "filter[cursus_id]": cursus_id,
                "range[begin_at]": f"{begin_at}T00:00:00Z,{end_at}T23:59:59Z",
            },
        )

    async def get_teams_by_ids(
        self, team_ids: list[int], *, batch_size: int = 75
    ) -> list[dict[str, Any]]:
        """Bulk-load full teams referenced by cohort project registrations."""
        if not team_ids:
            return []
        batches = [team_ids[index:index + batch_size] for index in range(0, len(team_ids), batch_size)]
        results = await asyncio.gather(*(
            self.get_all("/teams", params={"filter[id]": ",".join(map(str, batch))})
            for batch in batches
        ))
        return [item for result in results for item in result]


def deduplicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[Any, dict[str, Any]] = {}
    for item in items:
        key = item.get("id")
        if key is not None:
            by_id[key] = item
    return list(by_id.values())
