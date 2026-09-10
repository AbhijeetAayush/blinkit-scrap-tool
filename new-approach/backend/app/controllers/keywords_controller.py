from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies import CurrentUser, get_current_user, get_keyword_service
from app.schemas.keywords import (
    KeywordBulkRequest,
    KeywordBulkResponse,
    KeywordCreate,
    KeywordIdsResponse,
    KeywordListResponse,
    KeywordOut,
    KeywordUpdate,
)
from app.services.keyword_service import KeywordService

router = APIRouter(prefix="/api/v1/keywords", tags=["keywords"])


@router.get("", response_model=KeywordListResponse)
async def list_keywords(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[KeywordService, Depends(get_keyword_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    q: Annotated[str | None, Query()] = None,
) -> KeywordListResponse:
    items = await service.list(current.workspace_id, offset=offset, limit=limit, q=q)
    return KeywordListResponse(items=items)


@router.get("/ids", response_model=KeywordIdsResponse)
async def list_keyword_ids(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[KeywordService, Depends(get_keyword_service)],
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 2000,
) -> KeywordIdsResponse:
    return await service.list_ids(current.workspace_id, q=q, limit=limit)


@router.post("", response_model=KeywordOut, status_code=status.HTTP_201_CREATED)
async def create_keyword(
    body: KeywordCreate,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[KeywordService, Depends(get_keyword_service)],
) -> KeywordOut:
    return await service.create(current.workspace_id, query=body.query)


@router.post("/bulk", response_model=KeywordBulkResponse)
async def bulk_keywords(
    body: KeywordBulkRequest,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[KeywordService, Depends(get_keyword_service)],
) -> KeywordBulkResponse:
    return await service.bulk_upsert(current.workspace_id, body.queries)


@router.patch("/{keyword_id}", response_model=KeywordOut)
async def update_keyword(
    keyword_id: UUID,
    body: KeywordUpdate,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[KeywordService, Depends(get_keyword_service)],
) -> KeywordOut:
    return await service.update(
        current.workspace_id,
        keyword_id,
        query=body.query,
        active=body.active,
    )


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: UUID,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[KeywordService, Depends(get_keyword_service)],
) -> Response:
    await service.delete(current.workspace_id, keyword_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
