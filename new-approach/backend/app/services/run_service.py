from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.domain.models import RunStatus, ScrapeJob, chunk_queries
from app.domain.ports import JobQueue
from app.infrastructure.db.repositories.keyword_repo import KeywordRepository
from app.infrastructure.db.repositories.location_repo import LocationRepository
from app.infrastructure.db.repositories.run_repo import RunRepository
from app.infrastructure.queue.enqueue import ArqJobQueue
from app.schemas.runs import RunJobOut, RunOut


def _run_out(run, jobs: list[RunJobOut] | None = None) -> RunOut:
    return RunOut(
        id=run.id,
        workspace_id=run.workspace_id,
        status=run.status,
        pages_ok=run.pages_ok,
        pages_fail=run.pages_fail,
        jobs_total=run.jobs_total,
        jobs_done=run.jobs_done,
        error=run.error,
        started_at=run.started_at,
        finished_at=run.finished_at,
        jobs=jobs,
    )


class RunService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        queue: JobQueue | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._runs = RunRepository(session)
        self._keywords = KeywordRepository(session)
        self._locations = LocationRepository(session)
        self._queue = queue or ArqJobQueue()
        self._settings = settings or get_settings()

    async def start(
        self,
        workspace_id: UUID,
        *,
        keyword_ids: list[UUID],
        location_ids: list[UUID],
    ) -> RunOut:
        if not keyword_ids or not location_ids:
            raise DomainError("keyword_ids and location_ids must be non-empty")

        keywords = await self._keywords.get_by_ids(workspace_id, keyword_ids)
        if len(keywords) != len(set(keyword_ids)):
            raise NotFoundError("one or more keywords not found")
        inactive_kw = [k.query for k in keywords if not k.active]
        if inactive_kw:
            raise DomainError(f"inactive keywords: {', '.join(inactive_kw)}")

        locations = await self._locations.get_by_ids(workspace_id, location_ids)
        if len(locations) != len(set(location_ids)):
            raise NotFoundError("one or more locations not found")
        inactive_loc = [str(loc.id) for loc in locations if not loc.active]
        if inactive_loc:
            raise DomainError(f"inactive locations: {', '.join(inactive_loc)}")

        queries = [k.query for k in keywords]
        chunk_size = self._settings.queries_per_job
        scrape_jobs: list[ScrapeJob] = []

        run = await self._runs.create_run(
            workspace_id=workspace_id,
            status=RunStatus.queued.value,
            jobs_total=0,
        )

        for loc in locations:
            for chunk in chunk_queries(queries, chunk_size):
                run_job = await self._runs.create_run_job(
                    run_id=run.id,
                    platform=loc.platform,
                    location_id=loc.id,
                    queries=chunk,
                )
                scrape_jobs.append(
                    ScrapeJob(
                        run_id=run.id,
                        run_job_id=run_job.id,
                        workspace_id=workspace_id,
                        platform=loc.platform,
                        location_id=loc.id,
                        pincode=loc.pincode,
                        lat=loc.lat,
                        lon=loc.lon,
                        queries=chunk,
                    )
                )

        run.jobs_total = len(scrape_jobs)
        await self._session.flush()

        for job in scrape_jobs:
            await self._queue.enqueue_scrape(job)

        await self._runs.set_run_status(run.id, RunStatus.running.value)
        await self._session.commit()

        refreshed = await self._runs.get_by_id(run.id)
        assert refreshed is not None
        return _run_out(refreshed)

    async def list(self, workspace_id: UUID, *, limit: int = 50) -> list[RunOut]:
        rows = await self._runs.list_by_workspace(workspace_id, limit=limit)
        return [_run_out(r) for r in rows]

    async def get(self, workspace_id: UUID, run_id: UUID) -> RunOut:
        run = await self._runs.get_by_id(run_id, with_jobs=True)
        if not run:
            raise NotFoundError("run not found")
        if run.workspace_id != workspace_id:
            raise ForbiddenError("run not in workspace")
        jobs = [RunJobOut.model_validate(j) for j in (run.jobs or [])]
        return _run_out(run, jobs=jobs)
