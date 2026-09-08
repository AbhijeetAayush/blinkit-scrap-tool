from src.aws.http import response, signed_handler
from src.composition import build_app


def _run(payload: dict, _self_url: str) -> dict:
    app = build_app()
    ids = [str(i) for i in payload.get("pincode_ids") or []]
    return response(200, app.resolve.run(ids))


handler = signed_handler("resolve_function_url", _run)
