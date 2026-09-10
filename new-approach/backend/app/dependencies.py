from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.domain.errors import AuthError
from app.domain.ports import JobQueue
from app.infrastructure.db.session import get_session
from app.infrastructure.queue.enqueue import ArqJobQueue
from app.services.auth_service import AuthService, decode_access_token
from app.services.keyword_service import KeywordService
from app.services.location_service import LocationService
from app.services.run_service import RunService
from app.services.shelf_service import ShelfService

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    workspace_id: UUID


async def get_db(session: Annotated[AsyncSession, Depends(get_session)]) -> AsyncSession:
    return session


def get_settings_dep() -> Settings:
    return get_settings()


def get_job_queue() -> JobQueue:
    return ArqJobQueue()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    try:
        payload = decode_access_token(credentials.credentials, settings=settings)
        user_id = UUID(payload["sub"])
        workspace_id = UUID(payload["workspace_id"])
    except (AuthError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
        ) from exc
    return CurrentUser(user_id=user_id, workspace_id=workspace_id)


def get_auth_service(session: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    return AuthService(session)


def get_keyword_service(session: Annotated[AsyncSession, Depends(get_db)]) -> KeywordService:
    return KeywordService(session)


def get_location_service(session: Annotated[AsyncSession, Depends(get_db)]) -> LocationService:
    return LocationService(session)


def get_run_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    queue: Annotated[JobQueue, Depends(get_job_queue)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> RunService:
    return RunService(session, queue=queue, settings=settings)


def get_shelf_service(session: Annotated[AsyncSession, Depends(get_db)]) -> ShelfService:
    return ShelfService(session)
