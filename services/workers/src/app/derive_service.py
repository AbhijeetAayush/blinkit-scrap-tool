from __future__ import annotations

from typing import Any
from uuid import UUID

from src.derive.pipeline import DerivePipeline


class DeriveService:
    def __init__(self, pipeline: DerivePipeline) -> None:
        self._pipeline = pipeline

    def run(self, run_id: UUID) -> dict[str, Any]:
        return self._pipeline.run(run_id)
