from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, get_current_user, get_shelf_service
from app.schemas.shelf import ShelfListResponse
from app.services.shelf_service import ShelfService

router = APIRouter(prefix="/api/v1/shelf", tags=["shelf"])


@router.get("", response_model=ShelfListResponse)
async def list_shelf(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[ShelfService, Depends(get_shelf_service)],
    platform: Annotated[str | None, Query()] = None,
    pincode: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    merchant_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> ShelfListResponse:
    items = await service.list(
        current.workspace_id,
        platform=platform,
        pincode=pincode,
        q=q,
        merchant_id=merchant_id,
        limit=limit,
    )
    return ShelfListResponse(items=items, limit=limit)
