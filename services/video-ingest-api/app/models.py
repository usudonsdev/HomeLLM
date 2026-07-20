import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class VideoMatch(Base):
    __tablename__ = "video_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingest_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    game: Mapped[str] = mapped_column(String(32), nullable=False, default="valorant")
    source_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    lessons_learned: Mapped[str | None] = mapped_column(Text)
    emotional_log: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="analyzed")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    rounds: Mapped[list["VideoRound"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
        order_by="VideoRound.round_index",
        lazy="selectin",
    )


class VideoRound(Base):
    __tablename__ = "video_rounds"
    __table_args__ = (UniqueConstraint("match_id", "round_index", name="uq_video_round_match_index"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_matches.id", ondelete="CASCADE"), nullable=False
    )
    round_index: Mapped[int] = mapped_column(Integer, nullable=False)
    clip_path: Mapped[str] = mapped_column(Text, nullable=False)
    facts: Mapped[str | None] = mapped_column(Text)
    lessons_learned: Mapped[str | None] = mapped_column(Text)
    emotional_log: Mapped[str | None] = mapped_column(Text)
    highlight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    highlight_reason: Mapped[str | None] = mapped_column(Text)
    keyframe_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    match: Mapped[VideoMatch] = relationship(back_populates="rounds")
