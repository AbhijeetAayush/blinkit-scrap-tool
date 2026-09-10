from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.observation_repo import ObservationRepository
from app.schemas.shelf import ShelfRow


class ShelfService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ObservationRepository(session)

    async def list(
        self,
        workspace_id: UUID,
        *,
        platform: str | None = None,
        pincode: str | None = None,
        q: str | None = None,
        merchant_id: str | None = None,
        limit: int = 100,
    ) -> list[ShelfRow]:
        rows = await self._repo.list_latest(
            workspace_id,
            platform=platform.strip().lower() if platform else None,
            pincode=pincode.strip() if pincode else None,
            q=q.strip() if q else None,
            merchant_id=merchant_id.strip() if merchant_id else None,
            limit=max(1, min(limit, 500)),
        )
        return [ShelfRow.model_validate(row) for row in rows]
