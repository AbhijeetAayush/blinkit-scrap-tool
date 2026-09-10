from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KeywordCreate(BaseModel):
    query: str = Field(min_length=1)


class KeywordUpdate(BaseModel):
    query: str | None = None
    active: bool | None = None


class KeywordBulkRequest(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=2000)


class KeywordBulkResponse(BaseModel):
    read: int
    saved: int


class KeywordIdsResponse(BaseModel):
    ids: list[UUID]


class KeywordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    query: str
    active: bool
    created_at: datetime | None = None


class KeywordListResponse(BaseModel):
    items: list[KeywordOut]
