from datetime import datetime
from uuid import UUID

from src.aws.http import response, signed_handler
from src.composition import build_app
from src.domain.models import DispatchPayload


def _uuids(raw) -> list[UUID]:
    return [UUID(str(i)) for i in (raw or []) if i]


def _run(payload: dict, self_url: str) -> dict:
    app = build_app()
    slot = payload.get("observed_slot")
    run_id = payload.get("run_id")
    brand_id = payload.get("brand_id")
    data = DispatchPayload(
        continuation_offset=int(payload.get("continuation_offset") or 0),
        observed_slot=datetime.fromisoformat(slot) if slot else None,
        run_id=UUID(run_id) if run_id else None,
        slot_kind=payload.get("slot_kind") or "morning",
        self_url=payload.get("_self_url") or self_url,
        brand_id=UUID(str(brand_id)) if brand_id else None,
        keyword_ids=_uuids(payload.get("keyword_ids")),
        pincode_ids=_uuids(payload.get("pincode_ids")),
    )
    result = app.dispatch.run(data)
    return response(200, result)


handler = signed_handler("dispatch_function_url", _run)
