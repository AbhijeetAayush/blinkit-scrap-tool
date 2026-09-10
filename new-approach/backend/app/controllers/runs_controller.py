from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import CurrentUser, get_current_user, get_run_service
from app.schemas.runs import RunCreate, RunListResponse, RunOut
from app.services.run_service import RunService

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def start_run(
    body: RunCreate,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunOut:
    return await service.start(
        current.workspace_id,
        keyword_ids=body.keyword_ids,
        location_ids=body.location_ids,
    )


@router.get("", response_model=RunListResponse)
async def list_runs(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunListResponse:
    items = await service.list(current.workspace_id)
    return RunListResponse(items=items)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: UUID,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunOut:
    return await service.get(current.workspace_id, run_id)
