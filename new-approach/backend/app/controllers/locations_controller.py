from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies import CurrentUser, get_current_user, get_location_service
from app.schemas.locations import (
    LocationBulkRequest,
    LocationBulkResponse,
    LocationCreate,
    LocationIdsResponse,
    LocationListResponse,
    LocationOut,
    LocationUpdate,
)
from app.services.location_service import LocationService

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


@router.get("", response_model=LocationListResponse)
async def list_locations(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[LocationService, Depends(get_location_service)],
    platform: Annotated[str | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    q: Annotated[str | None, Query()] = None,
) -> LocationListResponse:
    items = await service.list(
        current.workspace_id,
        platform=platform,
        offset=offset,
        limit=limit,
        q=q,
    )
    return LocationListResponse(items=items)


@router.get("/ids", response_model=LocationIdsResponse)
async def list_location_ids(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[LocationService, Depends(get_location_service)],
    platform: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 2000,
) -> LocationIdsResponse:
    return await service.list_ids(current.workspace_id, platform=platform, q=q, limit=limit)


@router.post("", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreate,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[LocationService, Depends(get_location_service)],
) -> LocationOut:
    return await service.create(
        current.workspace_id,
        platform=body.platform,
        pincode=body.pincode,
        lat=body.lat,
        lon=body.lon,
        store_name=body.store_name,
    )


@router.post("/bulk", response_model=LocationBulkResponse)
async def bulk_locations(
    body: LocationBulkRequest,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[LocationService, Depends(get_location_service)],
) -> LocationBulkResponse:
    return await service.bulk_upsert(current.workspace_id, body.locations)


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: UUID,
    body: LocationUpdate,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[LocationService, Depends(get_location_service)],
) -> LocationOut:
    return await service.update(
        current.workspace_id,
        location_id,
        platform=body.platform,
        pincode=body.pincode,
        lat=body.lat,
        lon=body.lon,
        store_name=body.store_name,
        active=body.active,
    )


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: UUID,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[LocationService, Depends(get_location_service)],
) -> Response:
    await service.delete(current.workspace_id, location_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
