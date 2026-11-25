import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.database import Scan
from app.repositories.cache import CacheRepository
from app.schemas.scan import ScanCreate
from app.services.classification import classify, matches_promotion, reached_black_hole
from app.services.fixtures import fixture_data
from app.services.fortytwo import FortyTwoAPIError, FortyTwoClient, deduplicate

_tasks: dict[str, asyncio.Task] = {}


def users_from_cursus_users(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shape cursus-user index records like user records used by classification."""
    users: dict[int, dict[str, Any]] = {}
    for record in records:
        embedded = dict(record.get("user") or {})
        user_id = embedded.get("id")
        if user_id is None:
            continue
        user = users.setdefault(user_id, embedded)
        cursus_record = {key: value for key, value in record.items() if key != "user"}
        user.setdefault("cursus_users", []).append(cursus_record)
    return list(users.values())


async def create_scan(config: ScanCreate) -> Scan:
    settings = get_settings()
    scan = Scan(
        id=str(uuid4()), configuration=config.model_dump(mode="json"),
        source="demo" if settings.use_demo_data else "live",
    )
    async with SessionLocal() as session:
        session.add(scan)
        await session.commit()
        await session.refresh(scan)
    _tasks[scan.id] = asyncio.create_task(run_scan(scan.id))
    _tasks[scan.id].add_done_callback(lambda _task: _tasks.pop(scan.id, None))
    return scan


async def update_progress(scan_id: str, stage: str, completed: int, total: int) -> None:
    async with SessionLocal() as session:
        scan = await session.get(Scan, scan_id)
        if scan:
            scan.progress_stage = stage
            scan.completed_work = completed
            scan.total_work = total
            await session.commit()


async def run_scan(scan_id: str) -> None:
    settings = get_settings()
    client: FortyTwoClient | None = None
    warnings: list[str] = []
    teams_complete = True
    retrieval_times: list[datetime] = []
    try:
        async with SessionLocal() as session:
            scan = await session.get(Scan, scan_id)
            if not scan:
                return
            scan.status = "running"
            scan.started_at = datetime.now(timezone.utc)
            scan.progress_stage = "Preparing data sources"
            scan.total_work = 3
            await session.commit()
            config = ScanCreate.model_validate(scan.configuration)

        if settings.use_demo_data:
            await update_progress(scan_id, "Loading students", 0, 3)
            await asyncio.sleep(0.08)
            users, project_users, teams = fixture_data()
            await update_progress(scan_id, "Loading project registrations", 1, 3)
            await asyncio.sleep(0.08)
            await update_progress(scan_id, "Loading project teams", 2, 3)
            await asyncio.sleep(0.08)
        else:
            client = FortyTwoClient(settings)
            await update_progress(scan_id, "Loading campus students", 0, 3)
            promotion = config.promotion
            if promotion.type == "cursus_year":
                begin_at, end_at = f"{promotion.year}-01-01", f"{promotion.year}-12-31"
            elif promotion.type == "date_range":
                begin_at, end_at = str(promotion.start_date), str(promotion.end_date)
            else:
                begin_at = end_at = ""
            if promotion.type in {"cursus_year", "date_range"}:
                cursus_records, fetched_at, cached = await cached_collection(
                    "campus_cursus_users", f"{config.campus_id}:{begin_at}:{end_at}",
                    lambda: client.get_campus_cursus_users(config.campus_id, begin_at, end_at),
                    force=config.force_refresh,
                )
                users = users_from_cursus_users(cursus_records)
            else:
                users, fetched_at, cached = await cached_collection(
                    "campus_users", str(config.campus_id),
                    lambda: client.get_all(f"/campus/{config.campus_id}/users"),
                    force=config.force_refresh,
                )
            retrieval_times.append(fetched_at)
            if cached:
                warnings.append(f"Student metadata reused from cache ({fetched_at.isoformat()}).")
            eligible_user_ids = [
                user["id"] for user in users
                if user.get("id") is not None
                and matches_promotion(user, config.promotion)
                and not reached_black_hole(user)
            ]
            ended_cursus_count = sum(
                matches_promotion(user, config.promotion) and reached_black_hole(user)
                for user in users
            )
            if ended_cursus_count:
                warnings.append(
                    f"{ended_cursus_count} promotion students whose main 42 cursus has ended were excluded from peer results."
                )
            cohort_key = ":".join(map(str, (
                "cohort-v3", config.project_id, config.campus_id, promotion.type, promotion.year,
                promotion.month, promotion.start_date, promotion.end_date,
            )))
            await update_progress(scan_id, "Loading project registrations", 1, 3)
            project_users, fetched_at, cached = await cached_collection(
                "cohort_project_users", cohort_key,
                lambda: client.get_project_users(config.project_id, eligible_user_ids),
                force=config.force_refresh,
            )
            retrieval_times.append(fetched_at)
            if cached:
                warnings.append(f"Project registrations reused from cache ({fetched_at.isoformat()}).")
            await update_progress(scan_id, "Loading project teams", 2, 3)
            if config.project_solo:
                teams = []
            else:
                try:
                    team_ids = sorted({
                        team_id
                        for item in project_users
                        for team_id in (
                            [item.get("current_team_id")]
                            + [team.get("id") for team in (item.get("teams") or [])]
                        )
                        if team_id is not None
                    })
                    teams, fetched_at, cached = await cached_collection(
                        "cohort_teams", cohort_key,
                        lambda: client.get_teams_by_ids(team_ids),
                        force=config.force_refresh,
                    )
                    retrieval_times.append(fetched_at)
                    if cached:
                        warnings.append(f"Team records reused from cache ({fetched_at.isoformat()}).")
                except FortyTwoAPIError as exc:
                    async with SessionLocal() as session:
                        stale = await CacheRepository(session, settings.cache_ttl_seconds).get(
                            "cohort_teams", cohort_key, allow_stale=True
                        )
                    if stale:
                        teams, fetched_at = stale
                        retrieval_times.append(fetched_at)
                        warnings.append(f"The live team request failed; stale cached team data from {fetched_at.isoformat()} was used: {exc}")
                    else:
                        teams = []
                        teams_complete = False
                        warnings.append(f"Team records could not be fully loaded: {exc}")

        users, project_users, teams = map(deduplicate, (users, project_users, teams))
        students, team_results, summary = classify(
            config, users, project_users, teams, teams_complete=teams_complete
        )
        retrieved_at = min(retrieval_times) if retrieval_times else datetime.now(timezone.utc)
        result: dict[str, Any] = {
            "students": [item.model_dump(mode="json") for item in students],
            "teams": [item.model_dump(mode="json") for item in team_results],
            "summary": summary,
        }
        async with SessionLocal() as session:
            scan = await session.get(Scan, scan_id)
            if scan:
                scan.status = "completed"
                scan.progress_stage = "Complete"
                scan.completed_work = 3
                scan.total_work = 3
                scan.result = result
                scan.warnings = warnings
                scan.completed_at = retrieved_at
                scan.data_retrieved_at = retrieved_at
                await session.commit()
    except Exception as exc:
        async with SessionLocal() as session:
            scan = await session.get(Scan, scan_id)
            if scan:
                scan.status = "failed"
                scan.progress_stage = "Failed"
                scan.error = str(exc)
                scan.completed_at = datetime.now(timezone.utc)
                await session.commit()
    finally:
        if client:
            await client.close()


async def cached_collection(
    namespace: str,
    key: str,
    loader,
    *,
    force: bool,
) -> tuple[list[dict[str, Any]], datetime, bool]:
    """Return a TTL-cached API collection and its original retrieval time."""
    settings = get_settings()
    async with SessionLocal() as session:
        repository = CacheRepository(session, settings.cache_ttl_seconds)
        if not force:
            cached = await repository.get(namespace, key)
            if cached:
                payload, fetched_at = cached
                return payload, fetched_at, True
    payload = await loader()
    async with SessionLocal() as session:
        fetched_at = await CacheRepository(session, settings.cache_ttl_seconds).put(namespace, key, payload)
    return payload, fetched_at, False


async def recover_interrupted_scans() -> None:
    async with SessionLocal() as session:
        result = await session.scalars(select(Scan).where(Scan.status.in_(["queued", "running"])))
        for scan in result:
            scan.status = "failed"
            scan.error = "The server restarted before this scan completed. Please start a new scan."
            scan.progress_stage = "Interrupted"
            scan.completed_at = datetime.now(timezone.utc)
        await session.commit()
