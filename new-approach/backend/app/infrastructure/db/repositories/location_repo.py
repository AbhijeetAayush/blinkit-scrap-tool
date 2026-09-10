from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Location


class LocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_page(
        self,
        workspace_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
        platform: str | None = None,
        active_only: bool = False,
    ) -> list[Location]:
        stmt = select(Location).where(Location.workspace_id == workspace_id)
        if platform:
            stmt = stmt.where(Location.platform == platform)
        if active_only:
            stmt = stmt.where(Location.active.is_(True))
        if q:
            term = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Location.pincode.ilike(term),
                    Location.store_name.ilike(term),
                )
            )
        stmt = stmt.order_by(Location.pincode, Location.store_name).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_ids(
        self,
        workspace_id: UUID,
        *,
        q: str | None = None,
        platform: str | None = None,
        active_only: bool = True,
        limit: int = 2000,
    ) -> list[UUID]:
        stmt = select(Location.id).where(Location.workspace_id == workspace_id)
        if platform:
            stmt = stmt.where(Location.platform == platform)
        if active_only:
            stmt = stmt.where(Location.active.is_(True))
        if q:
            term = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Location.pincode.ilike(term),
                    Location.store_name.ilike(term),
                )
            )
        stmt = stmt.order_by(Location.pincode).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        platform: str | None = None,
    ) -> list[Location]:
        return await self.list_page(workspace_id, offset=0, limit=10_000, platform=platform)

    async def get_by_id(self, location_id: UUID) -> Location | None:
        return await self._session.get(Location, location_id)

    async def get_by_ids(self, workspace_id: UUID, ids: list[UUID]) -> list[Location]:
        if not ids:
            return []
        result = await self._session.execute(
            select(Location).where(Location.workspace_id == workspace_id, Location.id.in_(ids))
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        workspace_id: UUID,
        platform: str,
        pincode: str,
        lat: float,
        lon: float,
        store_name: str | None = None,
        active: bool = True,
    ) -> Location:
        row = Location(
            workspace_id=workspace_id,
            platform=platform,
            pincode=pincode,
            lat=lat,
            lon=lon,
            store_name=store_name,
            active=active,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def upsert_many(self, workspace_id: UUID, rows: list[dict]) -> int:
        if not rows:
            return 0
        payload = []
        for r in rows:
            payload.append(
                {
                    "workspace_id": workspace_id,
                    "platform": r["platform"],
                    "pincode": r["pincode"],
                    "lat": r["lat"],
                    "lon": r["lon"],
                    "store_name": r.get("store_name"),
                    "active": True,
                }
            )
        stmt = insert(Location).values(payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "platform", "lat", "lon"],
            set_={
                "pincode": stmt.excluded.pincode,
                "store_name": stmt.excluded.store_name,
                "active": True,
            },
        )
        await self._session.execute(stmt)
        return len(payload)

    async def update(
        self,
        location: Location,
        *,
        platform: str | None = None,
        pincode: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        store_name: str | None = None,
        active: bool | None = None,
    ) -> Location:
        if platform is not None:
            location.platform = platform
        if pincode is not None:
            location.pincode = pincode
        if lat is not None:
            location.lat = lat
        if lon is not None:
            location.lon = lon
        if store_name is not None:
            location.store_name = store_name
        if active is not None:
            location.active = active
        await self._session.flush()
        return location

    async def delete(self, location: Location) -> None:
        await self._session.delete(location)
        await self._session.flush()
