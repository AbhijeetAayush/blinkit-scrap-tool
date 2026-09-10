from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.infrastructure.db.repositories.keyword_repo import KeywordRepository
from app.schemas.keywords import KeywordBulkResponse, KeywordIdsResponse, KeywordOut


def normalize_keyword(query: str) -> str | None:
    cleaned = " ".join(query.strip().split()).lower()
    if not cleaned or cleaned == "others" or len(cleaned) < 3:
        return None
    return cleaned


def unique_keywords(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        q = normalize_keyword(raw)
        if not q or q in seen:
            continue
        seen.add(q)
        out.append(q)
    return out


class KeywordService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = KeywordRepository(session)

    async def list(
        self,
        workspace_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
    ) -> list[KeywordOut]:
        rows = await self._repo.list_page(
            workspace_id,
            offset=max(0, offset),
            limit=max(1, min(limit, 200)),
            q=q.strip() if q else None,
        )
        return [KeywordOut.model_validate(r) for r in rows]

    async def list_ids(
        self,
        workspace_id: UUID,
        *,
        q: str | None = None,
        limit: int = 2000,
    ) -> KeywordIdsResponse:
        ids = await self._repo.list_ids(
            workspace_id,
            q=q.strip() if q else None,
            active_only=True,
            limit=max(1, min(limit, 5000)),
        )
        return KeywordIdsResponse(ids=ids)

    async def create(self, workspace_id: UUID, *, query: str) -> KeywordOut:
        normalized = normalize_keyword(query)
        if not normalized:
            raise DomainError("keyword must be at least 3 characters and not 'Others'")
        try:
            row = await self._repo.create(workspace_id=workspace_id, query=normalized)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DomainError("keyword already exists") from exc
        return KeywordOut.model_validate(row)

    async def bulk_upsert(self, workspace_id: UUID, queries: list[str]) -> KeywordBulkResponse:
        unique = unique_keywords(queries)
        saved = 0
        chunk = 200
        for i in range(0, len(unique), chunk):
            saved += await self._repo.upsert_many(workspace_id, unique[i : i + chunk])
        await self._session.commit()
        return KeywordBulkResponse(read=len(queries), saved=saved)

    async def update(
        self,
        workspace_id: UUID,
        keyword_id: UUID,
        *,
        query: str | None = None,
        active: bool | None = None,
    ) -> KeywordOut:
        row = await self._require(workspace_id, keyword_id)
        new_query = normalize_keyword(query) if query is not None else None
        if query is not None and not new_query:
            raise DomainError("keyword must be at least 3 characters and not 'Others'")
        try:
            row = await self._repo.update(row, query=new_query, active=active)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DomainError("keyword already exists") from exc
        return KeywordOut.model_validate(row)

    async def delete(self, workspace_id: UUID, keyword_id: UUID) -> None:
        row = await self._require(workspace_id, keyword_id)
        await self._repo.delete(row)
        await self._session.commit()

    async def _require(self, workspace_id: UUID, keyword_id: UUID):
        row = await self._repo.get_by_id(keyword_id)
        if not row:
            raise NotFoundError("keyword not found")
        if row.workspace_id != workspace_id:
            raise ForbiddenError("keyword not in workspace")
        return row
