from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.domain.errors import AuthError, NotFoundError
from app.infrastructure.db.models import User, Workspace
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.schemas.auth import MeResponse, TokenResponse, UserOut, WorkspaceOut

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    *,
    user_id: UUID,
    workspace_id: UUID,
    settings: Settings | None = None,
) -> str:
    cfg = settings or get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=cfg.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "workspace_id": str(workspace_id),
        "exp": expire,
    }
    return jwt.encode(payload, cfg.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings | None = None) -> dict:
    cfg = settings or get_settings()
    try:
        return jwt.decode(token, cfg.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise AuthError("invalid or expired token") from exc


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._settings = settings or get_settings()

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    async def register(self, *, email: str, password: str, workspace_name: str) -> TokenResponse:
        normalized = self.normalize_email(email)
        existing = await self._users.get_by_email(normalized)
        if existing:
            raise AuthError("email already registered")
        user = await self._users.create_user(
            email=normalized,
            password_hash=hash_password(password),
        )
        workspace = await self._users.create_workspace(name=workspace_name.strip())
        await self._users.add_member(user_id=user.id, workspace_id=workspace.id, role="owner")
        await self._session.commit()
        return self._token_response(user, workspace)

    async def login(self, *, email: str, password: str) -> TokenResponse:
        normalized = self.normalize_email(email)
        user = await self._users.get_by_email(normalized)
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("invalid email or password")
        workspace = await self._users.get_workspace_for_user(user.id)
        if not workspace:
            raise AuthError("user has no workspace")
        return self._token_response(user, workspace)

    async def get_me(self, user_id: UUID) -> MeResponse:
        user = await self._users.get_by_id(user_id)
        if not user:
            raise NotFoundError("user not found")
        workspace = await self._users.get_workspace_for_user(user.id)
        if not workspace:
            raise NotFoundError("workspace not found")
        return MeResponse(
            user=UserOut.model_validate(user),
            workspace=WorkspaceOut.model_validate(workspace),
        )

    def _token_response(self, user: User, workspace: Workspace) -> TokenResponse:
        token = create_access_token(
            user_id=user.id,
            workspace_id=workspace.id,
            settings=self._settings,
        )
        return TokenResponse(
            access_token=token,
            user=UserOut.model_validate(user),
            workspace=WorkspaceOut.model_validate(workspace),
        )
