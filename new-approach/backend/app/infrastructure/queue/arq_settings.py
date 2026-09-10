from __future__ import annotations

from arq.connections import RedisSettings

from app.config import get_settings


def redis_settings_from_url(url: str | None = None) -> RedisSettings:
    return RedisSettings.from_dsn(url or get_settings().redis_url)


def get_redis_settings() -> RedisSettings:
    return redis_settings_from_url()
