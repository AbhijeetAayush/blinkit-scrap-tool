from datetime import datetime
from uuid import UUID

from src.aws.http import response, signed_handler
from src.composition import build_app
from src.domain.models import ScrapeJob


def _run(payload: dict, _self_url: str) -> dict:
    app = build_app()
    job = ScrapeJob(
        brand_ids=[UUID(b) for b in payload.get("brand_ids") or []],
        merchant_id=str(payload.get("merchant_id") or ""),
        platform=str(payload.get("platform") or "blinkit"),
        run_id=UUID(str(payload["run_id"])),
        correlation_id=str(payload.get("correlation_id") or payload["run_id"]),
        observed_slot=datetime.fromisoformat(str(payload["observed_slot"])),
    )
    return response(200, app.scrape.run(job))


handler = signed_handler("scrape_function_url", _run)
