import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["class", "intern", "project", "club", "event"]


class ExperienceCreate(BaseModel):
    category: Category
    title: str = Field(min_length=1, max_length=255)
    org_name: str | None = None
    start_date: date
    end_date: date | None = None
    description: str
    lessons_learned: str | None = None
    emotional_log: str | None = None
    tags: list[str] = Field(default_factory=list)


class ExperienceRead(BaseModel):
    id: uuid.UUID
    category: str
    title: str
    org_name: str | None
    start_date: date
    end_date: date | None
    description: str
    lessons_learned: str | None
    emotional_log: str | None
    tags: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class RagRequest(BaseModel):
    query: str = Field(min_length=1, description="面接用に引き出したいテーマ")
    keywords: list[str] = Field(default_factory=list, description="タグ / 検索キーワード")


class RagResponse(BaseModel):
    query: str
    matched_count: int
    context_titles: list[str]
    answer: str
    model: str
    ollama_reachable: bool
