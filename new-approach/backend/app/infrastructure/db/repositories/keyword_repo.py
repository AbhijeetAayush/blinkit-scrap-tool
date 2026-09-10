from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Keyword


class KeywordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_page(
        self,
        workspace_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
        active_only: bool = False,
    ) -> list[Keyword]:
        stmt = select(Keyword).where(Keyword.workspace_id == workspace_id)
        if active_only:
            stmt = stmt.where(Keyword.active.is_(True))
        if q:
            stmt = stmt.where(Keyword.query.ilike(f"%{q}%"))
        stmt = stmt.order_by(Keyword.query).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_ids(
        self,
        workspace_id: UUID,
        *,
        q: str | None = None,
        active_only: bool = True,
        limit: int = 2000,
    ) -> list[UUID]:
        stmt = select(Keyword.id).where(Keyword.workspace_id == workspace_id)
        if active_only:
            stmt = stmt.where(Keyword.active.is_(True))
        if q:
            stmt = stmt.where(Keyword.query.ilike(f"%{q}%"))
        stmt = stmt.order_by(Keyword.query).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_workspace(self, workspace_id: UUID) -> list[Keyword]:
        return await self.list_page(workspace_id, offset=0, limit=10_000)

    async def get_by_id(self, keyword_id: UUID) -> Keyword | None:
        return await self._session.get(Keyword, keyword_id)

    async def get_by_ids(self, workspace_id: UUID, ids: list[UUID]) -> list[Keyword]:
        if not ids:
            return []
        result = await self._session.execute(
            select(Keyword).where(Keyword.workspace_id == workspace_id, Keyword.id.in_(ids))
        )
        return list(result.scalars().all())

    async def create(self, *, workspace_id: UUID, query: str, active: bool = True) -> Keyword:
        row = Keyword(workspace_id=workspace_id, query=query, active=active)
        self._session.add(row)
        await self._session.flush()
        return row

    async def upsert_many(self, workspace_id: UUID, queries: list[str]) -> int:
        if not queries:
            return 0
        rows = [
            {"workspace_id": workspace_id, "query": q, "active": True}
            for q in queries
        ]
        stmt = insert(Keyword).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "query"],
            set_={"active": True},
        )
        await self._session.execute(stmt)
        return len(rows)

    async def update(
        self,
        keyword: Keyword,
        *,
        query: str | None = None,
        active: bool | None = None,
    ) -> Keyword:
        if query is not None:
            keyword.query = query
        if active is not None:
            keyword.active = active
        await self._session.flush()
        return keyword

    async def delete(self, keyword: Keyword) -> None:
        await self._session.delete(keyword)
        await self._session.flush()
