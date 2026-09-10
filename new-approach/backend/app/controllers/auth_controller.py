from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_auth_service, get_current_user
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return await service.register(
        email=body.email,
        password=body.password,
        workspace_name=body.workspace_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return await service.login(email=body.email, password=body.password)


@router.get("/me", response_model=MeResponse)
async def me(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MeResponse:
    return await service.get_me(current.user_id)
