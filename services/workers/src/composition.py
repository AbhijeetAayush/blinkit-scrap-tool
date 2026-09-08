from src.app.derive_service import DeriveService
from src.app.dispatch_service import DispatchService, ResolveStoresService
from src.app.scrape_store_service import ScrapeStoreService
from src.app.settings import Settings
from src.adapters.qstash_publisher import QStashPublisher
from src.adapters.redis_cache import RedisCache
from src.adapters.s3_lake import S3Lake
from src.adapters.supabase_repo import SupabaseRepos
from src.derive.alerts import Alerter
from src.derive.oos import OosTracker
from src.derive.pipeline import DerivePipeline
from src.platforms.registry import DefaultPlatformRegistry
from src.unlocker.router import StickyUnlockerRouter


class App:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        repos = SupabaseRepos(self.settings)
        redis = RedisCache(self.settings)
        publisher = QStashPublisher(self.settings)
        lake = S3Lake(self.settings)
        platforms = DefaultPlatformRegistry()
        router = StickyUnlockerRouter(self.settings, redis)
        oos = OosTracker(repos, repos, _VelocityAdapter(repos), self.settings.default_velocity, alerts=repos)
        pipeline = DerivePipeline(
            repos, lake, oos, Alerter(repos, repos), self.settings, runs=repos
        )
        self.resolve = ResolveStoresService(
            repos, repos, platforms, redis, router.location_unlocker()
        )
        self.dispatch = DispatchService(
            self.settings, repos, repos, repos, repos, publisher, redis, redis, platforms, self.resolve
        )
        self.scrape = ScrapeStoreService(
            self.settings,
            repos,
            repos,
            repos,
            repos,
            publisher,
            redis,
            redis,
            lake,
            platforms,
            router,
            review=repos,
        )
        self.derive = DeriveService(pipeline)


class _VelocityAdapter:
    def __init__(self, repos: SupabaseRepos) -> None:
        self._repos = repos

    def get(self, sku_id):
        return self._repos.get_velocity(sku_id)


def build_app(settings: Settings | None = None) -> App:
    return App(settings)
