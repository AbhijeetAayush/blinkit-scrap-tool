from __future__ import annotations

from typing import Any

from app.domain.models import ScrapeJob
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.queue.arq_settings import get_redis_settings
from app.services.scrape_service import ScrapeService


async def process_scrape_job(ctx: dict[str, Any], job_payload: dict[str, Any]) -> None:
    job = ScrapeJob.model_validate(job_payload)
    async with SessionLocal() as session:
        service = ScrapeService(session)
        try:
            await service.execute(job)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class WorkerSettings:
    redis_settings = get_redis_settings()
    functions = [process_scrape_job]
    max_jobs = 1
