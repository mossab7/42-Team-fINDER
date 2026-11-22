from typing import Any


def select_project_session(
    project: dict[str, Any], campus_id: int, *, cursus_id: int = 21
) -> dict[str, Any] | None:
    sessions = project.get("project_sessions") or []
    priorities = (
        lambda item: item.get("campus_id") == campus_id and item.get("cursus_id") == cursus_id,
        lambda item: item.get("campus_id") == campus_id,
        lambda item: item.get("cursus_id") == cursus_id,
        lambda _item: True,
    )
    for matches in priorities:
        selected = next((item for item in sessions if matches(item)), None)
        if selected:
            return selected
    return None


def derive_project_configuration(session: dict[str, Any] | None) -> dict[str, Any]:
    """Extract the official solo/group-size rule from a project session."""
    if not session:
        return {
            "project_session_id": None,
            "session_campus_id": None,
            "solo": False,
            "min_team_size": 2,
            "max_team_size": 5,
            "maximum_source": "fallback",
        }

    common = {
        "project_session_id": session.get("id"),
        "session_campus_id": session.get("campus_id"),
    }
    if session.get("solo") is True:
        return {
            **common,
            "solo": True,
            "min_team_size": 1,
            "max_team_size": 1,
            "maximum_source": "solo",
        }

    max_people = session.get("max_people")
    if isinstance(max_people, int) and max_people > 0:
        return {
            **common,
            "solo": False,
            "min_team_size": 2,
            "max_team_size": min(max_people, 20),
            "maximum_source": "max_people",
        }

    for project_rule in session.get("project_sessions_rules") or []:
        rule = project_rule.get("rule") or {}
        if rule.get("internal_name") != "GroupSizeBetweenNAndM":
            continue
        values: list[int] = []
        for param in project_rule.get("params") or []:
            try:
                value = int(param.get("value"))
            except (TypeError, ValueError):
                continue
            if value > 0:
                values.append(value)
        if values:
            return {
                **common,
                "solo": False,
                "min_team_size": min(values),
                "max_team_size": min(max(values), 20),
                "maximum_source": "group_rule",
            }

    return {
        **common,
        "solo": False,
        "min_team_size": 2,
        "max_team_size": 5,
        "maximum_source": "fallback",
    }
