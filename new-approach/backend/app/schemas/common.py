from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorBody(BaseModel):
    detail: str | dict | list


class ItemsResponse(BaseModel, Generic[T]):
    items: list[T]


class IdOut(BaseModel):
    id: UUID


class Timestamped(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime | None = None


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int | None = None
    limit: int = Field(default=100, ge=1)
