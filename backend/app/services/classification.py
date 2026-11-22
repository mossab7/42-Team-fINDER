from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.schemas.scan import PromotionDefinition, ScanCreate, StudentResult, TeamMember, TeamResult

COMPLETED_PROJECT_STATUSES = {"finished"}
UNAVAILABLE_TEAM_STATUSES = {"finished", "closed", "validated"}


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_date(value: str | None) -> date | None:
    parsed = parse_datetime(value)
    return parsed.date() if parsed else None


def primary_cursus(user: dict[str, Any]) -> dict[str, Any] | None:
    cursus_users = user.get("cursus_users") or []
    active = [item for item in cursus_users if not item.get("end_at")]
    candidates = active or cursus_users
    return max(candidates, key=lambda item: item.get("begin_at") or "", default=None)


def matches_promotion(user: dict[str, Any], promotion: PromotionDefinition) -> bool:
    if promotion.type == "piscine":
        month = (user.get("pool_month") or "").lower()
        expected_month = date(2000, promotion.month or 1, 1).strftime("%B").lower()
        return str(user.get("pool_year")) == str(promotion.year) and month == expected_month
    cursus = primary_cursus(user)
    begin = parse_date(cursus.get("begin_at") if cursus else None)
    if not begin:
        return False
    if promotion.type == "cursus_year":
        return begin.year == promotion.year
    return bool(promotion.start_date and promotion.end_date and promotion.start_date <= begin <= promotion.end_date)


def reached_black_hole(user: dict[str, Any], *, now: datetime | None = None) -> bool:
    """Return true only for a confirmed black-hole lifecycle transition.

    ``blackholed_at`` alone is a projected deadline and remains present for
    some active Cadets after that time.  It is therefore not sufficient proof
    that a student black-holed.  We only classify it as confirmed when the
    selected cursus was ended at approximately the same time as that deadline.
    """
    cursus = primary_cursus(user)
    if not cursus:
        return False
    blackholed_at = parse_datetime(cursus.get("blackholed_at"))
    ended_at = parse_datetime(cursus.get("end_at"))
    if not blackholed_at or not ended_at:
        return False
    current = now or datetime.now(timezone.utc)
    if blackholed_at > current or ended_at > current:
        return False
    return abs(ended_at - blackholed_at) <= timedelta(hours=36)


def project_completed(project_user: dict[str, Any] | None) -> bool:
    if not project_user:
        return False
    return project_user.get("status") in COMPLETED_PROJECT_STATUSES or (
        project_user.get("validated?") is True and project_user.get("final_mark") is not None
    )


def team_unavailable(team: dict[str, Any]) -> bool:
    return bool(
        team.get("closed?")
        or team.get("closed_at")
        or team.get("status") in UNAVAILABLE_TEAM_STATUSES
        or team.get("final_mark") is not None
    )


def image_url(user: dict[str, Any]) -> str | None:
    image = user.get("image")
    if isinstance(image, dict):
        return image.get("link") or (image.get("versions") or {}).get("small")
    return image if isinstance(image, str) else None


def classify(
    config: ScanCreate,
    users: list[dict[str, Any]],
    project_users: list[dict[str, Any]],
    teams: list[dict[str, Any]],
    *,
    teams_complete: bool = True,
) -> tuple[list[StudentResult], list[TeamResult], dict[str, int]]:
    promotion_members = [user for user in users if matches_promotion(user, config.promotion)]
    excluded_blackholed = [user for user in promotion_members if reached_black_hole(user)]
    eligible = [user for user in promotion_members if not reached_black_hole(user)]
    eligible_ids = {user["id"] for user in eligible}
    users_by_id = {user["id"]: user for user in users}
    project_by_user = {
        item.get("user", {}).get("id") or item.get("user_id"): item for item in project_users
    }
    active_team_by_user: dict[int, dict[str, Any]] = {}
    for team in teams:
        if team_unavailable(team):
            continue
        for member in team.get("users") or []:
            if member.get("id") is not None:
                active_team_by_user[member["id"]] = team

    student_results: list[StudentResult] = []
    for user in eligible:
        project_user = project_by_user.get(user["id"])
        team = active_team_by_user.get(user["id"])
        if project_completed(project_user):
            team_status = "completed"
            reason = "The project record is finished or API-validated."
        elif config.project_solo and project_user:
            team_status = "working_solo"
            reason = "The API reports an active registration for this solo project."
        elif team:
            team_status = "active_team"
            reason = f"API team membership found in {team.get('name', 'an active team')}."
        elif not teams_complete:
            team_status = "uncertain"
            reason = "Team data was incomplete, so absence of a team cannot be confirmed."
        elif not project_user:
            team_status = "not_registered"
            reason = "No project registration was returned; complete team data also shows no active membership."
        elif project_user.get("status") == "searching_a_group":
            team_status = "searching_group"
            reason = "The project registration explicitly reports searching_a_group."
        else:
            team_status = "registered_without_team"
            reason = "A project registration exists and complete team data shows no active membership."
        cursus = primary_cursus(user)
        student_results.append(
            StudentResult(
                id=user["id"], login=user.get("login", "unknown"),
                display_name=user.get("displayname") or user.get("usual_full_name") or user.get("login", "Unknown"),
                image_url=image_url(user), campus=config.campus_name or str(config.campus_id),
                promotion=promotion_label(config.promotion), level=cursus.get("level") if cursus else None,
                project_status=(project_user or {}).get("status", "not_registered"), team_status=team_status,
                profile_url=f"https://profile.intra.42.fr/users/{user.get('login', '')}",
                classification_reason=reason,
                available_data={"project_user": project_user, "cursus_user": cursus},
            )
        )

    team_results: list[TeamResult] = []
    for team in ([] if config.project_solo else teams):
        members = team.get("users") or []
        if not members or not any(member.get("id") in eligible_ids for member in members):
            continue
        unavailable = team_unavailable(team)
        count = len(members)
        below_limit = count < config.max_team_size
        locked = team.get("locked?") is True
        if unavailable or not below_limit:
            availability = "unavailable"
            reason = "The team is closed/completed or has reached the selected size limit."
        elif team.get("locked?") is False and team.get("status") == "creating_group":
            availability = "confirmed_joinable"
            reason = "The API reports an unlocked team that is creating its group."
        elif locked:
            availability = "potential_capacity"
            reason = "The team is below the selected size, but API locking means joinability is not confirmed."
        else:
            availability = "potential_capacity"
            reason = "Member count suggests capacity; the API does not explicitly confirm joinability."
        if availability == "unavailable" and not config.include_unavailable:
            continue
        resolved_members: list[TeamMember] = []
        for member in members:
            user = users_by_id.get(member.get("id"), member)
            login = user.get("login", "unknown")
            resolved_members.append(TeamMember(
                id=member.get("id", 0), login=login,
                display_name=user.get("displayname") or user.get("usual_full_name") or login,
                image_url=image_url(user), profile_url=f"https://profile.intra.42.fr/users/{login}",
                in_selected_promotion=member.get("id") in eligible_ids,
            ))
        team_results.append(TeamResult(
            id=team["id"], name=team.get("name", f"Team {team['id']}"),
            project=config.project_name or str(config.project_id), member_count=count,
            maximum_target_size=config.max_team_size, potential_spots=max(config.max_team_size - count, 0),
            status=team.get("status") or "unknown", members=resolved_members,
            availability=availability, classification_reason=reason,
        ))

    if config.project_solo:
        visible_students = [
            item for item in student_results
            if item.team_status == "working_solo" or (config.include_unavailable and item.team_status == "completed")
        ]
    else:
        visible_students = [
            item for item in student_results
            if config.include_unavailable or item.team_status not in {"active_team", "completed"}
        ]
    available_teams = [item for item in team_results if item.availability != "unavailable"]
    summary = {
        "total_eligible_students": len(eligible),
        "students_without_active_teams": sum(item.team_status in {"searching_group", "registered_without_team", "not_registered"} for item in student_results),
        "teams_below_size_limit": len(available_teams),
        "potentially_available_spots": sum(item.potential_spots for item in available_teams),
        "confirmed_joinable_spots": sum(item.potential_spots for item in available_teams if item.availability == "confirmed_joinable"),
        "students_working_on_project": sum(item.team_status == "working_solo" for item in student_results),
        "excluded_blackholed_students": len(excluded_blackholed),
    }
    return visible_students, team_results, summary


def promotion_label(promotion: PromotionDefinition) -> str:
    if promotion.type == "cursus_year":
        return f"Cursus {promotion.year}"
    if promotion.type == "piscine":
        return f"Piscine {date(2000, promotion.month or 1, 1).strftime('%B')} {promotion.year}"
    return f"{promotion.start_date} – {promotion.end_date}"
