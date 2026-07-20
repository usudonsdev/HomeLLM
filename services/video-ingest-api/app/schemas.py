import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VideoRoundIngest(BaseModel):
    round_index: int = Field(ge=1)
    clip_path: str = Field(min_length=1)
    facts: str | None = None
    lessons_learned: str | None = None
    emotional_log: str | None = None
    highlight: bool = False
    highlight_reason: str | None = None
    keyframe_paths: list[str] = Field(default_factory=list)


class VideoMatchIngest(BaseModel):
    ingest_job_id: uuid.UUID
    game: str = Field(default="valorant", min_length=1)
    source_filename: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=255)
    detail_analysis: str = Field(min_length=1)
    lessons_learned: str | None = None
    emotional_log: str | None = None
    status: str = "analyzed"
    rounds: list[VideoRoundIngest] = Field(default_factory=list)


class VideoRoundRead(BaseModel):
    id: uuid.UUID
    match_id: uuid.UUID
    round_index: int
    clip_path: str
    facts: str | None
    lessons_learned: str | None
    emotional_log: str | None
    highlight: bool
    highlight_reason: str | None
    keyframe_paths: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class VideoMatchSummaryRead(BaseModel):
    id: uuid.UUID
    ingest_job_id: uuid.UUID
    game: str
    source_filename: str
    title: str
    detail_analysis: str
    lessons_learned: str | None
    emotional_log: str | None
    status: str
    round_count: int
    highlight_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VideoMatchDetailRead(VideoMatchSummaryRead):
    rounds: list[VideoRoundRead]


class VideoRoundPatch(BaseModel):
    highlight: bool
    highlight_reason: str | None = None


class VideoTipsRequest(BaseModel):
    match_ids: list[uuid.UUID] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=5)


class VideoTipsResponse(BaseModel):
    round_ids: list[uuid.UUID]
    round_titles: list[str]
    matched_count: int
    answer: str
    model: str
    ollama_reachable: bool
