from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    keyword_ids: list[UUID] = Field(min_length=1)
    location_ids: list[UUID] = Field(min_length=1)


class RunJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: UUID
    platform: str
    status: str
    error: str | None = None
    queries: list[str] | None = None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    status: str
    pages_ok: int
    pages_fail: int
    jobs_total: int
    jobs_done: int
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    jobs: list[RunJobOut] | None = None


class RunListResponse(BaseModel):
    items: list[RunOut]
