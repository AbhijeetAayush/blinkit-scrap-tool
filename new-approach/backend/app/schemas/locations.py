from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    platform: str = "blinkit"
    pincode: str = Field(min_length=4, max_length=10)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    store_name: str | None = None


class LocationUpdate(BaseModel):
    platform: str | None = None
    pincode: str | None = Field(default=None, min_length=4, max_length=10)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    store_name: str | None = None
    active: bool | None = None


class LocationBulkItem(BaseModel):
    platform: str = "blinkit"
    pincode: str
    lat: float
    lon: float
    store_name: str | None = None


class LocationBulkRequest(BaseModel):
    locations: list[LocationBulkItem] = Field(min_length=1, max_length=2000)


class LocationBulkResponse(BaseModel):
    read: int
    saved: int
    skipped: int = 0


class LocationIdsResponse(BaseModel):
    ids: list[UUID]


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    platform: str
    pincode: str
    store_name: str | None = None
    lat: float
    lon: float
    active: bool
    created_at: datetime | None = None


class LocationListResponse(BaseModel):
    items: list[LocationOut]
