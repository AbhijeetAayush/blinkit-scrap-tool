from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.errors import DomainError, ForbiddenError, NotFoundError, UnknownPlatformError
from app.infrastructure.db.repositories.location_repo import LocationRepository
from app.platforms import registry
from app.schemas.locations import (
    LocationBulkItem,
    LocationBulkResponse,
    LocationIdsResponse,
    LocationOut,
)


def round_coord(n: float) -> float:
    return round(n * 1e6) / 1e6


class LocationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = LocationRepository(session)

    def _validate_platform(self, platform: str) -> str:
        key = (platform or "").strip().lower()
        if key not in registry.known_ids():
            raise UnknownPlatformError(f"unknown platform: {platform}")
        return key

    async def list(
        self,
        workspace_id: UUID,
        *,
        platform: str | None = None,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
    ) -> list[LocationOut]:
        plat = self._validate_platform(platform) if platform else None
        rows = await self._repo.list_page(
            workspace_id,
            offset=max(0, offset),
            limit=max(1, min(limit, 200)),
            q=q.strip() if q else None,
            platform=plat,
        )
        return [LocationOut.model_validate(r) for r in rows]

    async def list_ids(
        self,
        workspace_id: UUID,
        *,
        platform: str | None = None,
        q: str | None = None,
        limit: int = 2000,
    ) -> LocationIdsResponse:
        plat = self._validate_platform(platform) if platform else None
        ids = await self._repo.list_ids(
            workspace_id,
            q=q.strip() if q else None,
            platform=plat,
            active_only=True,
            limit=max(1, min(limit, 5000)),
        )
        return LocationIdsResponse(ids=ids)

    async def create(
        self,
        workspace_id: UUID,
        *,
        platform: str,
        pincode: str,
        lat: float,
        lon: float,
        store_name: str | None = None,
    ) -> LocationOut:
        plat = self._validate_platform(platform)
        pin = pincode.strip()
        if not (4 <= len(pin) <= 10):
            raise DomainError("pincode must be 4–10 characters")
        try:
            row = await self._repo.create(
                workspace_id=workspace_id,
                platform=plat,
                pincode=pin,
                lat=round_coord(lat),
                lon=round_coord(lon),
                store_name=store_name.strip() if store_name else None,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DomainError("location already exists for this platform/lat/lon") from exc
        return LocationOut.model_validate(row)

    async def bulk_upsert(
        self,
        workspace_id: UUID,
        items: list[LocationBulkItem],
    ) -> LocationBulkResponse:
        rows: list[dict] = []
        skipped = 0
        for item in items:
            try:
                plat = self._validate_platform(item.platform)
            except UnknownPlatformError:
                skipped += 1
                continue
            pin = item.pincode.strip()
            lat = round_coord(item.lat)
            lon = round_coord(item.lon)
            if not (4 <= len(pin) <= 10):
                skipped += 1
                continue
            rows.append(
                {
                    "platform": plat,
                    "pincode": pin,
                    "lat": lat,
                    "lon": lon,
                    "store_name": item.store_name.strip() if item.store_name else None,
                }
            )
        # de-dupe by platform/lat/lon keeping last
        dedup: dict[tuple, dict] = {}
        for r in rows:
            dedup[(r["platform"], r["lat"], r["lon"])] = r
        unique = list(dedup.values())
        saved = 0
        chunk = 200
        for i in range(0, len(unique), chunk):
            saved += await self._repo.upsert_many(workspace_id, unique[i : i + chunk])
        await self._session.commit()
        return LocationBulkResponse(read=len(items), saved=saved, skipped=skipped)

    async def update(
        self,
        workspace_id: UUID,
        location_id: UUID,
        *,
        platform: str | None = None,
        pincode: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        store_name: str | None = None,
        active: bool | None = None,
    ) -> LocationOut:
        row = await self._require(workspace_id, location_id)
        plat = self._validate_platform(platform) if platform is not None else None
        pin = pincode.strip() if pincode is not None else None
        if pin is not None and not (4 <= len(pin) <= 10):
            raise DomainError("pincode must be 4–10 characters")
        try:
            row = await self._repo.update(
                row,
                platform=plat,
                pincode=pin,
                lat=round_coord(lat) if lat is not None else None,
                lon=round_coord(lon) if lon is not None else None,
                store_name=store_name,
                active=active,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DomainError("location already exists for this platform/lat/lon") from exc
        return LocationOut.model_validate(row)

    async def delete(self, workspace_id: UUID, location_id: UUID) -> None:
        row = await self._require(workspace_id, location_id)
        await self._repo.delete(row)
        await self._session.commit()

    async def _require(self, workspace_id: UUID, location_id: UUID):
        row = await self._repo.get_by_id(location_id)
        if not row:
            raise NotFoundError("location not found")
        if row.workspace_id != workspace_id:
            raise ForbiddenError("location not in workspace")
        return row
