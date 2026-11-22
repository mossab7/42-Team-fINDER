"""42 authorization-code login and minimal, server-side browser sessions."""

import hashlib
import secrets
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.database import AuthSession, StudentProfile, utcnow

SESSION_COOKIE = "team_finder_session"
OAUTH_STATE_COOKIE = "team_finder_oauth_state"


def new_state() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authorization_url(settings: Settings, state: str) -> str:
    request = httpx.Request(
        "GET",
        "https://api.intra.42.fr/oauth/authorize",
        params={
            "client_id": settings.ft_client_id,
            "redirect_uri": settings.oauth_redirect_uri,
            "response_type": "code",
            "state": state,
        },
    )
    return str(request.url)


async def exchange_code(settings: Settings, code: str) -> dict[str, Any]:
    if not settings.ft_client_id or not settings.ft_client_secret:
        raise RuntimeError("42 OAuth credentials are not configured")
    async with httpx.AsyncClient(timeout=httpx.Timeout(settings.request_timeout_seconds)) as client:
        response = await client.post(
            settings.ft_token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.ft_client_id,
                "client_secret": settings.ft_client_secret,
                "code": code,
                "redirect_uri": settings.oauth_redirect_uri,
            },
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("42 OAuth did not return an access token")
        profile = await client.get(
            f"{settings.ft_api_base_url.rstrip('/')}/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        profile.raise_for_status()
        payload = profile.json()
    if not isinstance(payload, dict) or not payload.get("id") or not payload.get("login"):
        raise RuntimeError("42 OAuth returned an incomplete user profile")
    # A 42 identity must have at least one cursus enrollment. This prevents an
    # accidentally authorized non-student/service identity from seeing records.
    if not isinstance(payload.get("cursus_users"), list) or not payload["cursus_users"]:
        raise PermissionError("This 42 account has no student cursus enrollment")
    return payload


async def create_session(session: AsyncSession, settings: Settings, profile: dict[str, Any]) -> str:
    await sync_student_profile(session, profile)
    raw_token = secrets.token_urlsafe(48)
    expires_at = utcnow() + timedelta(hours=settings.session_ttl_hours)
    session.add(AuthSession(
        token_hash=token_hash(raw_token), user_id=int(profile["id"]), login=str(profile["login"]),
        display_name=str(profile.get("usual_full_name") or profile.get("displayname") or profile["login"]),
        expires_at=expires_at,
    ))
    await session.commit()
    return raw_token


async def sync_student_profile(session: AsyncSession, profile: dict[str, Any]) -> StudentProfile:
    """Refresh only identity fields managed by 42; preserve local preferences."""
    user_id = int(profile["id"])
    campus = next(iter(profile.get("campus") or profile.get("campus_users") or []), {}) or {}
    if "campus" in campus:
        campus = campus["campus"] or {}
    cursus = next(iter(profile.get("cursus_users") or []), {}) or {}
    image = profile.get("image") if isinstance(profile.get("image"), dict) else {}
    item = await session.get(StudentProfile, user_id)
    values = {
        "login": str(profile["login"]),
        "display_name": str(profile.get("usual_full_name") or profile.get("displayname") or profile["login"]),
        "image_url": image.get("versions", {}).get("medium") or image.get("link") or profile.get("image_url"),
        "campus_id": campus.get("id"), "campus_name": campus.get("name"), "level": cursus.get("level"),
    }
    if item:
        for key, value in values.items():
            setattr(item, key, value)
    else:
        item = StudentProfile(user_id=user_id, **values)
        session.add(item)
    await session.flush()
    return item


async def current_user(session: AsyncSession, raw_token: str | None) -> AuthSession | None:
    if not raw_token:
        return None
    record = await session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(raw_token)))
    if not record:
        return None
    expires_at = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=utcnow().tzinfo)
    if expires_at <= utcnow():
        await session.delete(record)
        await session.commit()
        return None
    return record


async def revoke_session(session: AsyncSession, raw_token: str | None) -> None:
    if raw_token:
        await session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(raw_token)))
        await session.commit()
