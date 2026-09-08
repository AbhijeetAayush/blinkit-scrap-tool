from uuid import UUID

from src.aws.http import response, signed_handler
from src.composition import build_app


def _run(payload: dict, _self_url: str) -> dict:
    app = build_app()
    return response(200, app.derive.run(UUID(str(payload["run_id"]))))


handler = signed_handler("derive_function_url", _run)
