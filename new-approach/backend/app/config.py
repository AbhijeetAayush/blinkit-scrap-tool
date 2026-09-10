from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    database_url: str = "postgresql+asyncpg://shelf:shelf@localhost:5432/shelf"
    redis_url: str = "redis://localhost:6379"
    jwt_secret: str = "change-me-min-32-chars-long-secret"
    jwt_expire_minutes: int = 10080
    cors_origins: str = "http://localhost:3000"
    queries_per_job: int = 6
    playwright_headless: bool = True
    playwright_nav_timeout_ms: int = 45000
    block_resource_types: str = "image,font,media"

    proxy_provider: str = "none"
    proxy_server: str = ""
    proxy_username: str = ""
    proxy_password: str = ""

    oxylabs_username: str = ""
    oxylabs_password: str = ""
    oxylabs_endpoint: str = "pr.oxylabs.io:7777"
    oxylabs_country: str = "IN"

    brightdata_customer: str = ""
    brightdata_zone: str = ""
    brightdata_password: str = ""
    brightdata_endpoint: str = "brd.superproxy.io:33335"
    brightdata_country: str = "in"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def block_types(self) -> list[str]:
        return [t.strip() for t in self.block_resource_types.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
