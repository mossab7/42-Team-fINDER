from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CacheEntry(Base):
    __tablename__ = "cache_entries"
    __table_args__ = (UniqueConstraint("namespace", "cache_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    namespace: Mapped[str] = mapped_column(String(64), index=True)
    cache_key: Mapped[str] = mapped_column(String(255))
    payload: Mapped[Any] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    progress_stage: Mapped[str] = mapped_column(String(80), default="Queued")
    completed_work: Mapped[int] = mapped_column(Integer, default=0)
    total_work: Mapped[int] = mapped_column(Integer, default=0)
    configuration: Mapped[Any] = mapped_column(JSON)
    result: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[Any] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(24), default="live")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    configuration: Mapped[Any] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    """A revocable, opaque browser session. No 42 access token is retained."""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    login: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# Matchmaking records deliberately use the immutable 42 user id.  The identity
# fields below are a local, refreshable projection used for privacy-safe UI;
# they are never accepted from a client as proof of identity.
class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(128), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    campus_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    campus_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    level: Mapped[float | None] = mapped_column(nullable=True)
    biography: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    availability: Mapped[str] = mapped_column(String(120), default="")
    working_hours: Mapped[str] = mapped_column(String(120), default="")
    github_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    visible: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Swipe(Base):
    __tablename__ = "swipes"
    __table_args__ = (
        UniqueConstraint("swiper_user_id", "target_user_id", "project_id", name="uq_swipe_pair_project"),
        Index("ix_swipes_target_project", "target_user_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    swiper_user_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), index=True)
    target_user_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), index=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    direction: Mapped[str] = mapped_column(String(8))  # left | right
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("project_id", "user_low_id", "user_high_id", name="uq_match_pair_project"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    project_name: Mapped[str] = mapped_column(String(255))
    user_low_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), index=True)
    user_high_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PlatformTeam(Base):
    __tablename__ = "platform_teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    project_name: Mapped[str] = mapped_column(String(255))
    campus_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    maximum_members: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PlatformTeamMember(Base):
    __tablename__ = "platform_team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_platform_team_member"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("platform_teams.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    status: Mapped[str] = mapped_column(String(20), default="accepted", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TeamInvitation(Base):
    __tablename__ = "team_invitations"
    __table_args__ = (UniqueConstraint("team_id", "recipient_id", name="uq_team_invitation_recipient"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("platform_teams.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), index=True)
    invited_by_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), index=True)
    type: Mapped[str] = mapped_column(String(48))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
