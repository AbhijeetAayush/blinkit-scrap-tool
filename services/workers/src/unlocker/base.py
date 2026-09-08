from src.domain.models import FetchResult


class BaseUnlocker:
    vendor: str = "base"

    def fetch(
        self,
        url: str,
        *,
        render: bool = False,
        country: str = "in",
        wait_for: str | None = None,
        cookies: str | None = None,
        js_scenario: dict | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> FetchResult:
        raise NotImplementedError
