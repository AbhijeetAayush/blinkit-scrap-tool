from __future__ import annotations

import logging

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.errors import ParseEmptyError
from app.domain.models import RunJobStatus, RunStatus, ScrapeJob, geo_merchant
from app.infrastructure.browser.playwright_factory import launch_session
from app.infrastructure.db.repositories.observation_repo import ObservationRepository
from app.infrastructure.db.repositories.run_repo import RunRepository
from app.platforms import registry

logger = logging.getLogger(__name__)


class ScrapeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._runs = RunRepository(session)
        self._observations = ObservationRepository(session)

    async def execute(self, job: ScrapeJob) -> None:
        await self._runs.mark_job_running(job.run_job_id)
        await self._session.commit()

        catalog = registry.get(job.platform)
        merchant_id = geo_merchant(job.lat, job.lon)
        session_id = f"{job.run_id}:{job.location_id}"
        fatal_error: str | None = None

        try:
            async with launch_session(session_id=session_id) as browser_session:
                for query in job.queries:
                    try:
                        listings = await catalog.search(
                            query,
                            lat=job.lat,
                            lon=job.lon,
                            session=browser_session,
                        )
                        await self._observations.upsert_many(
                            workspace_id=job.workspace_id,
                            run_id=job.run_id,
                            platform=job.platform,
                            merchant_id=merchant_id,
                            pincode=job.pincode,
                            listings=listings,
                        )
                        await self._runs.incr_pages_ok(job.run_id, 1)
                        await self._session.commit()
                    except (ParseEmptyError, PlaywrightTimeoutError, PlaywrightError, TimeoutError) as exc:
                        logger.warning(
                            "scrape query failed run=%s query=%r: %s",
                            job.run_id,
                            query,
                            exc,
                        )
                        await self._runs.incr_pages_fail(job.run_id, 1)
                        await self._session.commit()
                    except Exception as exc:
                        logger.exception(
                            "unexpected scrape query error run=%s query=%r",
                            job.run_id,
                            query,
                        )
                        await self._runs.incr_pages_fail(job.run_id, 1)
                        await self._session.commit()
                        # continue other queries; do not fail whole job on one query
                        _ = exc
        except Exception as exc:
            fatal_error = str(exc)[:2000]
            logger.exception("scrape job failed run_job=%s", job.run_job_id)

        terminal = RunJobStatus.failed.value if fatal_error else RunJobStatus.done.value
        transitioned = await self._runs.finish_job(
            job.run_job_id,
            status=terminal,
            error=fatal_error,
        )
        if transitioned:
            jobs_done, jobs_total = await self._runs.incr_jobs_done(job.run_id)
            if jobs_done >= jobs_total:
                await self._runs.finish_run(job.run_id, status=RunStatus.done.value)
        await self._session.commit()
