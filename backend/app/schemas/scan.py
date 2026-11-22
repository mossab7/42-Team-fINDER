from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


PromotionType = Literal["cursus_year", "piscine", "date_range"]


class PromotionDefinition(BaseModel):
    type: PromotionType = "cursus_year"
    year: int | None = None
    month: int | None = Field(default=None, ge=1, le=12)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_definition(self):
        if self.type in {"cursus_year", "piscine"} and self.year is None:
            raise ValueError("A year is required for this promotion definition")
        if self.type == "piscine" and self.month is None:
            raise ValueError("A month is required for a Piscine promotion")
        if self.type == "date_range":
            if not self.start_date or not self.end_date:
                raise ValueError("Both dates are required for a date range")
            if self.start_date > self.end_date:
                raise ValueError("The start date must be before the end date")
        return self


class ScanCreate(BaseModel):
    campus_id: int
    campus_name: str = ""
    project_id: int
    project_name: str = ""
    promotion: PromotionDefinition
    max_team_size: int = Field(default=5, ge=1, le=20)
    project_solo: bool = False
    include_unavailable: bool = False
    force_refresh: bool = False


class StudentResult(BaseModel):
    id: int
    login: str
    display_name: str
    image_url: str | None = None
    campus: str
    promotion: str
    level: float | None = None
    project_status: str
    team_status: Literal[
        "searching_group", "registered_without_team", "not_registered", "uncertain",
        "active_team", "working_solo", "completed"
    ]
    profile_url: str
    classification_reason: str
    available_data: dict = Field(default_factory=dict)


class TeamMember(BaseModel):
    id: int
    login: str
    display_name: str
    image_url: str | None = None
    profile_url: str
    in_selected_promotion: bool = False


class TeamResult(BaseModel):
    id: int
    name: str
    project: str
    member_count: int
    maximum_target_size: int
    potential_spots: int
    status: str
    members: list[TeamMember]
    availability: Literal["confirmed_joinable", "potential_capacity", "unavailable", "uncertain"]
    classification_reason: str


class ScanSummary(BaseModel):
    total_eligible_students: int
    students_without_active_teams: int
    teams_below_size_limit: int
    potentially_available_spots: int
    confirmed_joinable_spots: int = 0
    students_working_on_project: int = 0
    excluded_blackholed_students: int = 0


class ScanResponse(BaseModel):
    id: str
    status: str
    progress_stage: str
    completed_work: int
    total_work: int
    configuration: dict
    summary: ScanSummary | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    source: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    data_retrieved_at: datetime | None = None


class PaginatedStudents(BaseModel):
    items: list[StudentResult]
    total: int
    page: int
    page_size: int
    data_retrieved_at: datetime | None = None


class PaginatedTeams(BaseModel):
    items: list[TeamResult]
    total: int
    page: int
    page_size: int
    data_retrieved_at: datetime | None = None
