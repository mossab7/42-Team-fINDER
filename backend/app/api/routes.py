import csv
import io
import json
import httpx
from datetime import datetime, timezone, timedelta
from typing import Literal

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import delete, desc, select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.models.database import (CacheEntry, SavedSearch, Scan, StudentProfile, Swipe, Match,
                                 PlatformTeam, PlatformTeamMember, TeamInvitation, Notification)
from app.repositories.cache import CacheRepository
from app.schemas.scan import PaginatedStudents, PaginatedTeams, ScanCreate, ScanResponse, ScanSummary, StudentResult, TeamResult
from app.services.fixtures import CAMPUSES, PROJECTS, PROJECT_CONFIGURATIONS, USERS
from app.services.avatars import InvalidAvatarURL, fetch_avatar
from app.services.fortytwo import FortyTwoAPIError, FortyTwoClient
from app.services.project_configuration import derive_project_configuration, select_project_session
from app.services.scanner import create_scan
from app.services.auth import (OAUTH_STATE_COOKIE, SESSION_COOKIE, authorization_url, create_session,
                               current_user, exchange_code, new_state, revoke_session)

router = APIRouter(prefix="/api")


def set_cookie(response: Response, name: str, value: str, settings, *, max_age: int) -> None:
    response.set_cookie(name, value, max_age=max_age, httponly=True, secure=settings.session_cookie_secure,
                        samesite="lax", path="/")


@router.get("/auth/me")
async def auth_me(request: Request, session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    user = await current_user(session, request.cookies.get(SESSION_COOKIE))
    return {
        "auth_required": settings.auth_required,
        "authenticated": bool(user),
        "user": None if not user else {"id": user.user_id, "login": user.login, "display_name": user.display_name},
    }


@router.get("/auth/login")
async def auth_login():
    settings = get_settings()
    if not settings.ft_client_id or not settings.ft_client_secret:
        raise HTTPException(503, "42 OAuth credentials are not configured")
    state = new_state()
    response = RedirectResponse(authorization_url(settings, state), status_code=302)
    set_cookie(response, OAUTH_STATE_COOKIE, state, settings, max_age=600)
    return response


@router.get("/auth/callback")
async def auth_callback(request: Request, code: str | None = None, state: str | None = None,
                        error: str | None = None, session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    failure_url = f"{settings.public_base_url.rstrip('/')}/?auth=failed"
    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if error or not code or not state or not expected_state or not secrets.compare_digest(state, expected_state):
        return RedirectResponse(failure_url, status_code=302)
    try:
        profile = await exchange_code(settings, code)
        raw_token = await create_session(session, settings, profile)
    except PermissionError:
        return RedirectResponse(f"{failure_url}&reason=not_student", status_code=302)
    except (httpx.HTTPError, RuntimeError):
        return RedirectResponse(failure_url, status_code=302)
    response = RedirectResponse(f"{settings.public_base_url.rstrip('/')}/?auth=success", status_code=302)
    set_cookie(response, SESSION_COOKIE, raw_token, settings, max_age=settings.session_ttl_hours * 3600)
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    return response


@router.post("/auth/logout")
async def auth_logout(request: Request, session: AsyncSession = Depends(get_session)):
    await revoke_session(session, request.cookies.get(SESSION_COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


def compact_metadata(namespace: str, payload: list[dict]) -> list[dict]:
    if namespace == "projects":
        return [
            {key: item.get(key) for key in ("id", "name", "slug")}
            for item in payload
        ]
    if namespace == "campuses":
        return [
            {key: item.get(key) for key in ("id", "name", "city", "country")}
            for item in payload
        ]
    return payload


def scan_response(scan: Scan) -> ScanResponse:
    summary = ScanSummary.model_validate(scan.result["summary"]) if scan.result else None
    return ScanResponse(
        id=scan.id, status=scan.status, progress_stage=scan.progress_stage,
        completed_work=scan.completed_work, total_work=scan.total_work,
        configuration=scan.configuration, summary=summary, warnings=scan.warnings or [], error=scan.error,
        source=scan.source, created_at=scan.created_at, started_at=scan.started_at,
        completed_at=scan.completed_at, data_retrieved_at=scan.data_retrieved_at,
    )


async def metadata(namespace: str, key: str, path: str, session: AsyncSession, force: bool = False) -> tuple[list[dict], datetime]:
    settings = get_settings()
    source = "demo" if settings.use_demo_data else "live"
    # Demo fixtures and live API payloads must never share a cache entry. This
    # matters when credentials are added after the application has already run
    # in demo mode using the same persistent SQLite database.
    namespace = f"{namespace}:{source}"
    cache = CacheRepository(session, settings.cache_ttl_seconds)
    if not force:
        cached = await cache.get(namespace, key)
        if cached:
            payload, fetched_at = cached
            return compact_metadata(namespace.split(":", 1)[0], payload), fetched_at
    if settings.use_demo_data:
        payload = CAMPUSES if namespace == "campuses" else PROJECTS
    else:
        client = FortyTwoClient(settings)
        try:
            payload = await client.get_all(path)
        finally:
            await client.close()
    payload = compact_metadata(namespace.split(":", 1)[0], payload)
    fetched = await cache.put(namespace, key, payload)
    return payload, fetched


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    await session.execute(select(1))
    return {
        "status": "ok", "api_mode": "demo" if settings.use_demo_data else "live",
        "api_configured": bool(settings.ft_client_id and settings.ft_client_secret),
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/avatars")
async def avatar(url: str = Query(..., min_length=1, max_length=2048)):
    """Same-origin proxy for OAuth-protected images from the official 42 CDN."""
    settings = get_settings()
    if settings.use_demo_data:
        raise HTTPException(404, "Avatar proxy is only available with live 42 API credentials")
    try:
        path, content_type, cache_hit = await fetch_avatar(url, settings)
    except InvalidAvatarURL as exc:
        raise HTTPException(400, str(exc)) from exc
    except FortyTwoAPIError as exc:
        raise HTTPException(502, "Unable to load this avatar from the 42 CDN") from exc
    return FileResponse(
        path,
        media_type=content_type,
        headers={
            "Cache-Control": f"private, max-age={settings.avatar_cache_ttl_seconds}",
            "X-Avatar-Cache": "HIT" if cache_hit else "MISS",
        },
    )


@router.get("/campuses")
async def campuses(force_refresh: bool = False, session: AsyncSession = Depends(get_session)):
    try:
        items, fetched_at = await metadata("campuses", "all", "/campus", session, force_refresh)
        return {"items": items, "fetched_at": fetched_at, "source": "demo" if get_settings().use_demo_data else "live"}
    except FortyTwoAPIError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/projects")
async def projects(search: str = "", force_refresh: bool = False, session: AsyncSession = Depends(get_session)):
    try:
        items, fetched_at = await metadata("projects", "all", "/projects", session, force_refresh)
        if search:
            items = [item for item in items if search.lower() in item.get("name", "").lower()]
        return {"items": items, "fetched_at": fetched_at, "source": "demo" if get_settings().use_demo_data else "live"}
    except FortyTwoAPIError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/projects/{project_id}/configuration")
async def project_configuration(
    project_id: int,
    campus_id: int,
    force_refresh: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Return the selected campus session's official solo/team-size settings."""
    settings = get_settings()
    source = "demo" if settings.use_demo_data else "live"
    cache = CacheRepository(session, settings.cache_ttl_seconds)
    namespace = f"project_configuration:{source}"
    key = f"{project_id}:{campus_id}"
    if not force_refresh:
        cached = await cache.get(namespace, key)
        if cached:
            payload, fetched_at = cached
            return {**payload, "fetched_at": fetched_at, "source": source}

    try:
        if settings.use_demo_data:
            payload = PROJECT_CONFIGURATIONS.get(project_id) or derive_project_configuration(None)
        else:
            client = FortyTwoClient(settings)
            try:
                project_response = await client.request("GET", f"/projects/{project_id}")
                project = project_response.json()
                selected = select_project_session(project, campus_id)
                if selected:
                    detail_response = await client.request("GET", f"/project_sessions/{selected['id']}")
                    payload = derive_project_configuration(detail_response.json())
                else:
                    payload = derive_project_configuration(None)
            finally:
                await client.close()
        payload = {"project_id": project_id, "campus_id": campus_id, **payload}
        fetched_at = await cache.put(namespace, key, payload)
        return {**payload, "fetched_at": fetched_at, "source": source}
    except FortyTwoAPIError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/promotions")
async def promotions(campus_id: int):
    if get_settings().use_demo_data:
        years = sorted({int(c["begin_at"][:4]) for u in USERS for c in u.get("cursus_users", [])}, reverse=True)
    else:
        current = datetime.now(timezone.utc).year
        years = list(range(current, current - 8, -1))
    return {"campus_id": campus_id, "cursus_years": years, "definitions": ["cursus_year", "piscine", "date_range"]}


@router.post("/scans", response_model=ScanResponse, status_code=202)
async def start_scan(payload: ScanCreate):
    return scan_response(await create_scan(payload))


@router.get("/scans", response_model=list[ScanResponse])
async def scans(limit: int = Query(20, ge=1, le=100), session: AsyncSession = Depends(get_session)):
    items = await session.scalars(select(Scan).order_by(desc(Scan.created_at)).limit(limit))
    return [scan_response(item) for item in items]


@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str, session: AsyncSession = Depends(get_session)):
    scan = await session.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    return scan_response(scan)


def completed_scan(scan: Scan | None) -> Scan:
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.status != "completed" or not scan.result:
        raise HTTPException(409, "Scan results are not ready")
    return scan


@router.get("/scans/{scan_id}/students", response_model=PaginatedStudents)
async def scan_students(
    scan_id: str, search: str = "", status: str = "", sort: Literal["login", "level", "-level"] = "login",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    scan = completed_scan(await session.get(Scan, scan_id))
    items = [StudentResult.model_validate(item) for item in scan.result["students"]]
    if search:
        needle = search.lower()
        items = [item for item in items if needle in item.login.lower() or needle in item.display_name.lower()]
    if status:
        items = [item for item in items if item.team_status == status]
    items.sort(key=(lambda x: x.login.lower()) if sort == "login" else (lambda x: x.level or -1), reverse=sort == "-level")
    total = len(items)
    start = (page - 1) * page_size
    return PaginatedStudents(items=items[start:start + page_size], total=total, page=page, page_size=page_size, data_retrieved_at=scan.data_retrieved_at)


@router.get("/scans/{scan_id}/teams", response_model=PaginatedTeams)
async def scan_teams(
    scan_id: str, status: str = "", sort: Literal["size", "-size", "spots"] = "size",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    scan = completed_scan(await session.get(Scan, scan_id))
    items = [TeamResult.model_validate(item) for item in scan.result["teams"]]
    if status:
        items = [item for item in items if item.availability == status]
    items.sort(key=(lambda x: x.potential_spots) if sort == "spots" else (lambda x: x.member_count), reverse=sort == "-size")
    total = len(items)
    start = (page - 1) * page_size
    return PaginatedTeams(items=items[start:start + page_size], total=total, page=page, page_size=page_size, data_retrieved_at=scan.data_retrieved_at)


@router.get("/scans/{scan_id}/export")
async def export_scan(scan_id: str, format: Literal["csv", "json"] = "csv", session: AsyncSession = Depends(get_session)):
    scan = completed_scan(await session.get(Scan, scan_id))
    if format == "json":
        body = json.dumps({"scan": scan.configuration, **scan.result}, indent=2)
        return Response(body, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="scan-{scan_id}.json"'})
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["record_type", "login_or_team", "display_name", "status", "member_count", "potential_spots", "profile_url"])
    for item in scan.result["students"]:
        writer.writerow(["student", item["login"], item["display_name"], item["team_status"], "", "", item["profile_url"]])
    for item in scan.result["teams"]:
        writer.writerow(["team", item["name"], "", item["availability"], item["member_count"], item["potential_spots"], ""])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="scan-{scan_id}.csv"'})


@router.delete("/cache", status_code=204)
async def clear_cache(session: AsyncSession = Depends(get_session)):
    await session.execute(delete(CacheEntry))
    await session.commit()
    return Response(status_code=204)


@router.get("/saved-searches")
async def saved_searches(session: AsyncSession = Depends(get_session)):
    items = await session.scalars(select(SavedSearch).order_by(desc(SavedSearch.created_at)))
    return [{"id": item.id, "name": item.name, "configuration": item.configuration, "created_at": item.created_at} for item in items]


@router.post("/saved-searches", status_code=201)
async def save_search(payload: dict, session: AsyncSession = Depends(get_session)):
    if not payload.get("name") or not payload.get("configuration"):
        raise HTTPException(422, "name and configuration are required")
    item = SavedSearch(name=str(payload["name"])[:120], configuration=payload["configuration"])
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": item.id, "name": item.name, "configuration": item.configuration, "created_at": item.created_at}


# --- Matchmaking ---------------------------------------------------------
# A scan is the authoritative eligibility snapshot.  Matchmaking deliberately
# never treats an absent record as eligible; both people must be present in the
# same completed scan before a swipe can result in a match or team invitation.

async def matchmaking_actor(request: Request, session: AsyncSession) -> StudentProfile:
    auth = getattr(request.state, "auth_user", None)
    if auth is None:
        auth = await current_user(session, request.cookies.get(SESSION_COOKIE))
    if auth is None:
        raise HTTPException(401, "Sign in with a 42 student account to use matchmaking")
    profile = await session.get(StudentProfile, auth.user_id)
    if profile is None:
        # Repair sessions created before matchmaking profiles existed.
        profile = StudentProfile(user_id=auth.user_id, login=auth.login, display_name=auth.display_name)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


def profile_payload(profile: StudentProfile, *, include_contact: bool = False) -> dict:
    data = {"user_id": profile.user_id, "login": profile.login, "display_name": profile.display_name,
            "image_url": profile.image_url, "campus_id": profile.campus_id, "campus_name": profile.campus_name,
            "level": profile.level, "biography": profile.biography, "skills": profile.skills or [],
            "languages": profile.languages or [], "availability": profile.availability,
            "working_hours": profile.working_hours, "visible": profile.visible,
            "updated_at": profile.updated_at}
    if include_contact:
        data["github_url"] = profile.github_url
    return data


def matching_eligible(item: dict) -> bool:
    """Only subscribed, unlocked group-project registrations enter matching."""
    if item.get("team_status") not in {"searching_group", "registered_without_team"}:
        return False
    registration = (item.get("available_data") or {}).get("project_user") or {}
    return bool(registration) and registration.get("locked?") is not True and not registration.get("marked_at")


def eligible_student_ids(scan: Scan) -> set[int]:
    """The two statuses are explicit scanner evidence of a peer opportunity."""
    return {int(item["id"]) for item in (scan.result or {}).get("students", []) if matching_eligible(item)}


def project_details(scan: Scan, project_id: int) -> tuple[str, int, int | None] | None:
    config = scan.configuration or {}
    if int(config.get("project_id", -1)) != project_id:
        return None
    project = config.get("project") or {}
    constraints = config.get("project_constraints") or {}
    maximum = int(constraints.get("maximum_team_size") or config.get("max_team_size") or 1)
    return (str(project.get("name") or config.get("project_name") or f"Project {project_id}"), maximum,
            config.get("campus_id"))


async def latest_project_scan(session: AsyncSession, project_id: int, campus_id: int | None = None) -> Scan:
    scans = (await session.scalars(select(Scan).where(Scan.status == "completed").order_by(desc(Scan.completed_at)).limit(100))).all()
    for scan in scans:
        details = project_details(scan, project_id)
        if details and (campus_id is None or details[2] in {None, campus_id}):
            return scan
    raise HTTPException(409, "No completed eligibility scan is available for this project. Run a scan in Explore first.")


async def actor_has_active_group_registration(actor: StudentProfile, project_id: int, session: AsyncSession) -> bool:
    """Verify the caller's own registration before exposing/swiping peers."""
    if get_settings().use_demo_data:
        try:
            return actor.user_id in eligible_student_ids(await latest_project_scan(session, project_id, actor.campus_id))
        except HTTPException:
            return False
    if not actor.campus_id:
        return False
    client = FortyTwoClient(get_settings())
    try:
        rows = await client.get_all("/projects_users", params={"filter[user_id]": actor.user_id,
                                                                  "filter[project_id]": project_id})
        registration = next((item for item in rows if item.get("status") in {"in_progress", "searching_a_group", "waiting_to_start"}
                             and not item.get("marked_at") and item.get("validated?") is not True
                             and not item.get("current_team_id")), None)
        if not registration:
            return False
        project = (await client.request("GET", f"/projects/{project_id}")).json()
        return not derive_project_configuration(select_project_session(project, actor.campus_id))["solo"]
    except FortyTwoAPIError:
        return False
    finally:
        await client.close()


async def active_match_for(session: AsyncSession, user_id: int, other_id: int, project_id: int) -> Match | None:
    low, high = sorted((user_id, other_id))
    return await session.scalar(select(Match).where(Match.project_id == project_id, Match.user_low_id == low,
                                                     Match.user_high_id == high, Match.status == "active"))


@router.get("/discover/projects")
async def discover_projects(request: Request, session: AsyncSession = Depends(get_session)):
    actor = await matchmaking_actor(request, session)
    # The selector is based on the student's own current 42 registrations,
    # rather than merely whether they happened to be in an older cohort scan.
    # We still require a completed scan later to safely enumerate peers.
    if not get_settings().use_demo_data and actor.campus_id:
        client = FortyTwoClient(get_settings())
        try:
            registrations = await client.get_all("/projects_users", params={"filter[user_id]": actor.user_id})
            items: list[dict] = []
            for registration in registrations:
                status = registration.get("status")
                project = registration.get("project") or {}
                project_id = project.get("id") or registration.get("project_id")
                if (not isinstance(project_id, int) or status not in {"in_progress", "searching_a_group", "waiting_to_start"}
                        or registration.get("marked_at") or registration.get("validated?") is True
                        or registration.get("current_team_id")):
                    continue
                detail = (await client.request("GET", f"/projects/{project_id}")).json()
                constraints = derive_project_configuration(select_project_session(detail, actor.campus_id))
                if constraints["solo"]:
                    continue
                items.append({"id": project_id, "name": project.get("name") or detail.get("name") or f"Project {project_id}",
                              "maximum_team_size": constraints["max_team_size"], "campus_id": actor.campus_id,
                              "scanned_at": None})
            return {"items": items, "source": "your active 42 project registrations"}
        except FortyTwoAPIError as exc:
            # The scan fallback remains useful during temporary 42 rate limits.
            fallback_warning = str(exc)
        finally:
            await client.close()
    else:
        fallback_warning = None
    scans = (await session.scalars(select(Scan).where(Scan.status == "completed").order_by(desc(Scan.completed_at)).limit(100))).all()
    seen: set[int] = set(); items: list[dict] = []
    for scan in scans:
        config = scan.configuration or {}; project_id = config.get("project_id")
        if not isinstance(project_id, int) or project_id in seen:
            continue
        details = project_details(scan, project_id)
        if not details or details[1] <= 1 or (actor.campus_id and details[2] and actor.campus_id != details[2]):
            continue
        # The project is exposed only when this student has explicit scan evidence too.
        if actor.user_id not in eligible_student_ids(scan):
            continue
        seen.add(project_id)
        items.append({"id": project_id, "name": details[0], "maximum_team_size": details[1],
                      "campus_id": details[2], "scanned_at": scan.data_retrieved_at or scan.completed_at})
    return {"items": items, "source": "completed eligibility scans", "warning": fallback_warning}


@router.get("/discover/candidates")
async def discover_candidates(project_id: int, level_min: float | None = None, level_max: float | None = None,
                              skill: str = "", availability: str = "", request: Request = None,
                              session: AsyncSession = Depends(get_session)):
    actor = await matchmaking_actor(request, session)
    scan = await latest_project_scan(session, project_id, actor.campus_id)
    if not await actor_has_active_group_registration(actor, project_id, session):
        raise HTTPException(403, "Your active 42 registration for this group project could not be verified.")
    target_ids = eligible_student_ids(scan) - {actor.user_id}
    if not target_ids:
        return {"items": [], "scan_id": scan.id, "data_retrieved_at": scan.data_retrieved_at}
    swiped = set((await session.scalars(select(Swipe.target_user_id).where(Swipe.swiper_user_id == actor.user_id,
                         Swipe.project_id == project_id))).all())
    items = []
    for result in (scan.result or {}).get("students", []):
        if int(result.get("id", -1)) not in target_ids or int(result.get("id", -1)) in swiped:
            continue
        level = result.get("level")
        if level_min is not None and (level is None or level < level_min): continue
        if level_max is not None and (level is None or level > level_max): continue
        # Candidate cards use the current scanner's 42 API payload only. There
        # are intentionally no user-maintained skills, biography, or contact fields.
        items.append({"user_id": int(result["id"]), "login": result.get("login", "unknown"),
                      "display_name": result.get("display_name", result.get("login", "Unknown")),
                      "image_url": result.get("image_url"), "campus_name": result.get("campus"),
                      "campus_id": actor.campus_id, "level": level, "biography": "", "skills": [],
                      "languages": [], "availability": "", "working_hours": "", "github_url": None,
                      "visible": True})
    items.sort(key=lambda item: (item["level"] is None, item["login"].lower()))
    return {"items": items, "scan_id": scan.id, "data_retrieved_at": scan.data_retrieved_at}


@router.post("/swipes")
async def create_swipe(payload: dict, request: Request, session: AsyncSession = Depends(get_session)):
    actor = await matchmaking_actor(request, session)
    try:
        target_id, project_id = int(payload["target_user_id"]), int(payload["project_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(422, "target_user_id and project_id are required") from exc
    direction = payload.get("direction")
    if direction not in {"left", "right"} or target_id == actor.user_id:
        raise HTTPException(422, "Use left or right for another student")
    scan = await latest_project_scan(session, project_id, actor.campus_id)
    eligible = eligible_student_ids(scan)
    target = await session.get(StudentProfile, target_id)
    if target_id not in eligible or not await actor_has_active_group_registration(actor, project_id, session):
        raise HTTPException(403, "Both students must be verified as eligible in the same completed scan")
    swipe = await session.scalar(select(Swipe).where(Swipe.swiper_user_id == actor.user_id,
        Swipe.target_user_id == target_id, Swipe.project_id == project_id))
    if swipe: swipe.direction = direction
    else: session.add(Swipe(swiper_user_id=actor.user_id, target_user_id=target_id, project_id=project_id, direction=direction))
    matched = False; match = None
    if direction == "right":
        reciprocal = await session.scalar(select(Swipe).where(Swipe.swiper_user_id == target_id,
            Swipe.target_user_id == actor.user_id, Swipe.project_id == project_id, Swipe.direction == "right"))
        if reciprocal:
            # A reciprocal swipe can only be made by an authenticated student,
            # whose minimal verified identity row is created by matchmaking_actor.
            if target is None:
                raise HTTPException(409, "The other student's verified session is no longer available")
            low, high = sorted((actor.user_id, target_id)); match = await active_match_for(session, actor.user_id, target_id, project_id)
            if not match:
                name, _, _ = project_details(scan, project_id) or (f"Project {project_id}", 1, None)
                match = Match(project_id=project_id, project_name=name, user_low_id=low, user_high_id=high)
                session.add(match); await session.flush()
                for recipient, other in ((actor, target), (target, actor)):
                    session.add(Notification(recipient_id=recipient.user_id, type="match", title="New mutual match",
                        body=f"You and {other.display_name} matched for {name}.", payload={"match_id": match.id, "project_id": project_id}))
            matched = True
    await session.commit()
    return {"direction": direction, "matched": matched, "match_id": match.id if match else None}


@router.get("/matches")
async def list_matches(request: Request, session: AsyncSession = Depends(get_session)):
    actor = await matchmaking_actor(request, session)
    matches = (await session.scalars(select(Match).where(Match.status == "active", or_(Match.user_low_id == actor.user_id,
                    Match.user_high_id == actor.user_id)).order_by(desc(Match.created_at)))).all()
    items = []
    for match in matches:
        other_id = match.user_high_id if match.user_low_id == actor.user_id else match.user_low_id
        other = await session.get(StudentProfile, other_id)
        if other: items.append({"id": match.id, "project_id": match.project_id, "project_name": match.project_name,
                                 "created_at": match.created_at, "profile": profile_payload(other, include_contact=True)})
    return {"items": items}


@router.delete("/matches/{match_id}", status_code=204)
async def remove_match(match_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    actor = await matchmaking_actor(request, session); match = await session.get(Match, match_id)
    if not match or actor.user_id not in {match.user_low_id, match.user_high_id}: raise HTTPException(404, "Match not found")
    match.status = "removed"; await session.commit(); return Response(status_code=204)


@router.get("/notifications")
async def list_notifications(request: Request, session: AsyncSession = Depends(get_session)):
    actor = await matchmaking_actor(request, session)
    # SQLite storage is not billed by row, but bounded retention is good privacy
    # hygiene and prevents unbounded volume growth. Matches themselves persist.
    await session.execute(delete(Notification).where((Notification.created_at < utcnow() - timedelta(days=5)) | (Notification.type != "match")))
    await session.commit()
    items = (await session.scalars(select(Notification).where(Notification.recipient_id == actor.user_id, Notification.type == "match").order_by(desc(Notification.created_at)).limit(100))).all()
    return {"items": [{"id": n.id, "type": n.type, "title": n.title, "body": n.body, "payload": n.payload,
                        "read": n.read, "created_at": n.created_at} for n in items]}


@router.patch("/notifications/{notification_id}")
async def read_notification(notification_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    actor = await matchmaking_actor(request, session); item = await session.get(Notification, notification_id)
    if not item or item.recipient_id != actor.user_id: raise HTTPException(404, "Notification not found")
    item.read = True; await session.commit(); return {"id": item.id, "read": True}


async def team_payload(session: AsyncSession, team: PlatformTeam) -> dict:
    members = (await session.scalars(select(PlatformTeamMember).where(PlatformTeamMember.team_id == team.id,
                PlatformTeamMember.status == "accepted"))).all()
    profiles = {p.user_id: p for p in (await session.scalars(select(StudentProfile).where(
        StudentProfile.user_id.in_([m.user_id for m in members] or [-1])))).all()}
    return {"id": team.id, "project_id": team.project_id, "project_name": team.project_name, "name": team.name,
            "description": team.description, "maximum_members": team.maximum_members, "status": team.status,
            "creator_id": team.creator_id, "campus_id": team.campus_id, "created_at": team.created_at,
            "members": [{"role": member.role, "profile": profile_payload(profiles[member.user_id])}
                        for member in members if member.user_id in profiles],
            "available_spots": max(0, team.maximum_members - len(members))}


@router.get("/teams")
async def list_platform_teams(project_id: int | None = None, request: Request = None,
                              session: AsyncSession = Depends(get_session)):
    raise HTTPException(410, "Platform teams are no longer part of this service")
    actor = await matchmaking_actor(request, session)
    member_team_ids = select(PlatformTeamMember.team_id).where(PlatformTeamMember.user_id == actor.user_id,
                                                                 PlatformTeamMember.status == "accepted")
    statement = select(PlatformTeam).where(or_(PlatformTeam.id.in_(member_team_ids),
        PlatformTeam.status.in_(["recruiting", "pending"]))).order_by(desc(PlatformTeam.created_at))
    if project_id is not None: statement = statement.where(PlatformTeam.project_id == project_id)
    teams = (await session.scalars(statement)).all()
    return {"items": [await team_payload(session, team) for team in teams]}


@router.post("/teams", status_code=201)
async def create_team(payload: dict, request: Request, session: AsyncSession = Depends(get_session)):
    raise HTTPException(410, "Platform teams are no longer part of this service")
    actor = await matchmaking_actor(request, session)
    try: match_id = int(payload["match_id"])
    except (KeyError, ValueError, TypeError) as exc: raise HTTPException(422, "match_id is required") from exc
    match = await session.get(Match, match_id)
    if not match or match.status != "active" or actor.user_id not in {match.user_low_id, match.user_high_id}:
        raise HTTPException(403, "A current mutual match is required to create a team")
    scan = await latest_project_scan(session, match.project_id, actor.campus_id)
    name, maximum, campus_id = project_details(scan, match.project_id) or (match.project_name, 1, actor.campus_id)
    if maximum <= 1: raise HTTPException(409, "This project is not a collaborative project")
    team_name = str(payload.get("name") or f"{name} team")[:120].strip()
    if not team_name: raise HTTPException(422, "A team name is required")
    team = PlatformTeam(project_id=match.project_id, project_name=name, campus_id=campus_id, creator_id=actor.user_id,
                        name=team_name, description=str(payload.get("description") or "")[:1000],
                        maximum_members=maximum, status="pending")
    session.add(team); await session.flush()
    session.add(PlatformTeamMember(team_id=team.id, user_id=actor.user_id, role="creator", status="accepted"))
    recipient_id = match.user_high_id if match.user_low_id == actor.user_id else match.user_low_id
    invitation = TeamInvitation(team_id=team.id, recipient_id=recipient_id, invited_by_id=actor.user_id)
    session.add(invitation)
    session.add(Notification(recipient_id=recipient_id, type="team_invitation", title="Team invitation",
        body=f"{actor.display_name} invited you to join {team_name} for {name}.", payload={"team_id": team.id}))
    await session.commit(); await session.refresh(team)
    return await team_payload(session, team)


@router.get("/team-invitations")
async def list_team_invitations(request: Request, session: AsyncSession = Depends(get_session)):
    raise HTTPException(410, "Platform teams are no longer part of this service")
    actor = await matchmaking_actor(request, session)
    invitations = (await session.scalars(select(TeamInvitation).where(TeamInvitation.recipient_id == actor.user_id,
                     TeamInvitation.status == "pending").order_by(desc(TeamInvitation.created_at)))).all()
    result = []
    for invite in invitations:
        team = await session.get(PlatformTeam, invite.team_id); sender = await session.get(StudentProfile, invite.invited_by_id)
        if team: result.append({"id": invite.id, "status": invite.status, "team": await team_payload(session, team),
                                "invited_by": profile_payload(sender) if sender else None})
    return {"items": result}


@router.post("/team-invitations/{invitation_id}/respond")
async def respond_team_invitation(invitation_id: int, payload: dict, request: Request,
                                  session: AsyncSession = Depends(get_session)):
    raise HTTPException(410, "Platform teams are no longer part of this service")
    actor = await matchmaking_actor(request, session); invite = await session.get(TeamInvitation, invitation_id)
    if not invite or invite.recipient_id != actor.user_id or invite.status != "pending": raise HTTPException(404, "Invitation not found")
    accept = bool(payload.get("accept")); team = await session.get(PlatformTeam, invite.team_id)
    if not team or team.status == "cancelled": raise HTTPException(409, "This team is no longer available")
    if accept:
        count = await session.scalar(select(func.count()).select_from(PlatformTeamMember).where(
            PlatformTeamMember.team_id == team.id, PlatformTeamMember.status == "accepted"))
        if (count or 0) >= team.maximum_members: raise HTTPException(409, "This team is full")
        existing = await session.scalar(select(PlatformTeamMember).where(PlatformTeamMember.team_id == team.id,
                                                                          PlatformTeamMember.user_id == actor.user_id))
        if not existing: session.add(PlatformTeamMember(team_id=team.id, user_id=actor.user_id, status="accepted"))
        team.status = "ready" if (count or 0) + 1 >= team.maximum_members else "recruiting"
        invite.status = "accepted"; message = f"{actor.display_name} joined {team.name}."
    else:
        invite.status = "declined"; message = f"{actor.display_name} declined the invitation to {team.name}."
    session.add(Notification(recipient_id=team.creator_id, type="team_response", title="Team invitation update",
                             body=message, payload={"team_id": team.id}))
    await session.commit(); return {"invitation_id": invite.id, "status": invite.status, "team": await team_payload(session, team)}


@router.delete("/teams/{team_id}/members/me", status_code=204)
async def leave_team(team_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    raise HTTPException(410, "Platform teams are no longer part of this service")
    actor = await matchmaking_actor(request, session); team = await session.get(PlatformTeam, team_id)
    membership = await session.scalar(select(PlatformTeamMember).where(PlatformTeamMember.team_id == team_id,
        PlatformTeamMember.user_id == actor.user_id, PlatformTeamMember.status == "accepted"))
    if not team or not membership: raise HTTPException(404, "Team membership not found")
    await session.delete(membership)
    if team.creator_id == actor.user_id:
        successor = await session.scalar(select(PlatformTeamMember).where(PlatformTeamMember.team_id == team_id,
                                      PlatformTeamMember.status == "accepted").order_by(PlatformTeamMember.created_at))
        if successor:
            team.creator_id = successor.user_id; successor.role = "creator"
        else: team.status = "cancelled"
    await session.commit(); return Response(status_code=204)
