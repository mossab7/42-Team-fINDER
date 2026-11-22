from copy import deepcopy

CAMPUS = {"id": 1, "name": "Paris", "city": "Paris", "country": "France"}
CAMPUSES = [
    CAMPUS,
    {"id": 2, "name": "42 Abu Dhabi", "city": "Abu Dhabi", "country": "United Arab Emirates"},
    {"id": 3, "name": "42 Berlin", "city": "Berlin", "country": "Germany"},
]
PROJECTS = [
    {"id": 101, "name": "ft_transcendence", "slug": "ft-transcendence"},
    {"id": 102, "name": "webserv", "slug": "webserv"},
    {"id": 103, "name": "minishell", "slug": "minishell"},
    {"id": 104, "name": "Libft", "slug": "42cursus-libft"},
]

PROJECT_CONFIGURATIONS = {
    101: {"project_session_id": 1001, "session_campus_id": 1, "solo": False, "min_team_size": 4, "max_team_size": 5, "maximum_source": "group_rule"},
    102: {"project_session_id": 1002, "session_campus_id": 1, "solo": False, "min_team_size": 2, "max_team_size": 3, "maximum_source": "group_rule"},
    103: {"project_session_id": 1003, "session_campus_id": 1, "solo": False, "min_team_size": 2, "max_team_size": 2, "maximum_source": "group_rule"},
    104: {"project_session_id": 1004, "session_campus_id": 1, "solo": True, "min_team_size": 1, "max_team_size": 1, "maximum_source": "solo"},
}

USERS = [
    {"id": 1, "login": "ada", "displayname": "Ada Lovelace", "image": {"link": "https://api.dicebear.com/9.x/initials/svg?seed=Ada"}, "campus": [CAMPUS], "cursus_users": [{"begin_at": "2024-09-02T08:00:00Z", "level": 6.42, "cursus": {"id": 21, "name": "42cursus"}}], "pool_year": "2024", "pool_month": "september"},
    {"id": 2, "login": "linus", "displayname": "Linus Torvalds", "image": {"link": "https://api.dicebear.com/9.x/initials/svg?seed=Linus"}, "campus": [CAMPUS], "cursus_users": [{"begin_at": "2024-10-01T08:00:00Z", "level": 5.11, "cursus": {"id": 21, "name": "42cursus"}}], "pool_year": "2024", "pool_month": "september"},
    {"id": 3, "login": "grace", "displayname": "Grace Hopper", "image": {"link": "https://api.dicebear.com/9.x/initials/svg?seed=Grace"}, "campus": [CAMPUS], "cursus_users": [{"begin_at": "2024-11-03T08:00:00Z", "level": 7.05, "cursus": {"id": 21, "name": "42cursus"}}], "pool_year": "2024", "pool_month": "october"},
    {"id": 4, "login": "margaret", "displayname": "Margaret Hamilton", "image": {"link": "https://api.dicebear.com/9.x/initials/svg?seed=Margaret"}, "campus": [CAMPUS], "cursus_users": [{"begin_at": "2024-09-15T08:00:00Z", "level": 4.89, "cursus": {"id": 21, "name": "42cursus"}}], "pool_year": "2024", "pool_month": "september"},
    {"id": 5, "login": "alan", "displayname": "Alan Turing", "image": {"link": "https://api.dicebear.com/9.x/initials/svg?seed=Alan"}, "campus": [CAMPUS], "cursus_users": [{"begin_at": "2024-09-28T08:00:00Z", "level": 8.21, "cursus": {"id": 21, "name": "42cursus"}}], "pool_year": "2024", "pool_month": "september"},
    {"id": 6, "login": "katherine", "displayname": "Katherine Johnson", "image": {"link": "https://api.dicebear.com/9.x/initials/svg?seed=Katherine"}, "campus": [{"id": 2, "name": "42 Abu Dhabi"}], "cursus_users": [{"begin_at": "2023-09-28T08:00:00Z", "level": 6.9, "cursus": {"id": 21, "name": "42cursus"}}], "pool_year": "2023", "pool_month": "september"},
]

PROJECT_USERS = [
    {"id": 201, "user": {"id": 1, "login": "ada"}, "project": PROJECTS[0], "status": "searching_a_group", "validated?": False, "final_mark": None},
    {"id": 202, "user": {"id": 2, "login": "linus"}, "project": PROJECTS[0], "status": "in_progress", "validated?": False, "final_mark": None},
    {"id": 203, "user": {"id": 4, "login": "margaret"}, "project": PROJECTS[0], "status": "in_progress", "validated?": False, "final_mark": None},
    {"id": 204, "user": {"id": 5, "login": "alan"}, "project": PROJECTS[0], "status": "finished", "validated?": True, "final_mark": 110},
    {"id": 205, "user": {"id": 6, "login": "katherine"}, "project": PROJECTS[0], "status": "in_progress", "validated?": False, "final_mark": None},
]

TEAMS = [
    {"id": 301, "name": "kernel-panic", "project_id": 101, "status": "in_progress", "final_mark": None, "locked?": False, "closed?": False, "users": [{"id": 2, "login": "linus", "projects_user_id": 202}, {"id": 6, "login": "katherine", "projects_user_id": 205}]},
    {"id": 302, "name": "apollo", "project_id": 101, "status": "in_progress", "final_mark": None, "locked?": True, "closed?": False, "users": [{"id": 4, "login": "margaret", "projects_user_id": 203}]},
    {"id": 303, "name": "enigma", "project_id": 101, "status": "finished", "final_mark": 110, "locked?": True, "closed?": True, "users": [{"id": 5, "login": "alan", "projects_user_id": 204}]},
]


def fixture_data() -> tuple[list[dict], list[dict], list[dict]]:
    return deepcopy(USERS), deepcopy(PROJECT_USERS), deepcopy(TEAMS)
