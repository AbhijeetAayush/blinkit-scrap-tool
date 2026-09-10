from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis

from app.domain.models import ScrapeJob
from app.infrastructure.queue.arq_settings import get_redis_settings

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        # arq exposes create_pool at package level (returns ArqRedis)
        _pool = await create_pool(get_redis_settings())
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close(close_connection_pool=True)
        _pool = None


class ArqJobQueue:
    async def enqueue_scrape(self, job: ScrapeJob) -> None:
        pool = await get_arq_pool()
        await pool.enqueue_job("process_scrape_job", job.model_dump(mode="json"))


async def enqueue_scrape(job: ScrapeJob) -> None:
    await ArqJobQueue().enqueue_scrape(job)
