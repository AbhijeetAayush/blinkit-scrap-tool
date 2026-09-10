from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import User, Workspace, WorkspaceMember


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(self, *, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash)
        self._session.add(user)
        await self._session.flush()
        return user

    async def create_workspace(self, *, name: str) -> Workspace:
        workspace = Workspace(name=name)
        self._session.add(workspace)
        await self._session.flush()
        return workspace

    async def add_member(self, *, user_id: UUID, workspace_id: UUID, role: str) -> WorkspaceMember:
        member = WorkspaceMember(user_id=user_id, workspace_id=workspace_id, role=role)
        self._session.add(member)
        await self._session.flush()
        return member

    async def get_membership(self, user_id: UUID) -> WorkspaceMember | None:
        result = await self._session.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return await self._session.get(Workspace, workspace_id)

    async def get_workspace_for_user(self, user_id: UUID) -> Workspace | None:
        result = await self._session.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .limit(1)
        )
        return result.scalar_one_or_none()
