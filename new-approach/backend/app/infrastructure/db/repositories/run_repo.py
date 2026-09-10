from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import RunJobStatus, RunStatus, utcnow
from app.infrastructure.db.models import Run, RunJob


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(
        self,
        *,
        workspace_id: UUID,
        status: str,
        jobs_total: int,
    ) -> Run:
        run = Run(
            workspace_id=workspace_id,
            status=status,
            jobs_total=jobs_total,
            jobs_done=0,
            pages_ok=0,
            pages_fail=0,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def create_run_job(
        self,
        *,
        run_id: UUID,
        platform: str,
        location_id: UUID,
        queries: list[str],
        status: str = RunJobStatus.pending.value,
    ) -> RunJob:
        job = RunJob(
            run_id=run_id,
            platform=platform,
            location_id=location_id,
            queries=queries,
            status=status,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def set_run_status(self, run_id: UUID, status: str) -> None:
        await self._session.execute(update(Run).where(Run.id == run_id).values(status=status))

    async def list_by_workspace(self, workspace_id: UUID, *, limit: int = 50) -> list[Run]:
        result = await self._session.execute(
            select(Run)
            .where(Run.workspace_id == workspace_id)
            .order_by(Run.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, run_id: UUID, *, with_jobs: bool = False) -> Run | None:
        stmt = select(Run).where(Run.id == run_id)
        if with_jobs:
            stmt = stmt.options(selectinload(Run.jobs))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def incr_pages_ok(self, run_id: UUID, amount: int = 1) -> None:
        await self._session.execute(
            update(Run).where(Run.id == run_id).values(pages_ok=Run.pages_ok + amount)
        )

    async def incr_pages_fail(self, run_id: UUID, amount: int = 1) -> None:
        await self._session.execute(
            update(Run).where(Run.id == run_id).values(pages_fail=Run.pages_fail + amount)
        )

    async def mark_job_running(self, run_job_id: UUID) -> None:
        await self._session.execute(
            update(RunJob)
            .where(
                RunJob.id == run_job_id,
                RunJob.status == RunJobStatus.pending.value,
            )
            .values(status=RunJobStatus.running.value, attempts=RunJob.attempts + 1)
        )

    async def finish_job(
        self,
        run_job_id: UUID,
        *,
        status: str,
        error: str | None = None,
    ) -> bool:
        """Transition pending/running → done|failed. Returns True if this call won the transition."""
        result = await self._session.execute(
            update(RunJob)
            .where(
                RunJob.id == run_job_id,
                RunJob.status.in_(
                    [RunJobStatus.pending.value, RunJobStatus.running.value]
                ),
            )
            .values(status=status, error=error, finished_at=utcnow())
            .returning(RunJob.id)
        )
        return result.scalar_one_or_none() is not None

    async def incr_jobs_done(self, run_id: UUID) -> tuple[int, int]:
        """Increment jobs_done once; return (jobs_done, jobs_total)."""
        result = await self._session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(jobs_done=Run.jobs_done + 1)
            .returning(Run.jobs_done, Run.jobs_total)
        )
        row = result.one()
        return int(row[0]), int(row[1])

    async def finish_run(self, run_id: UUID, *, status: str = RunStatus.done.value) -> None:
        await self._session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(status=status, finished_at=utcnow())
        )
