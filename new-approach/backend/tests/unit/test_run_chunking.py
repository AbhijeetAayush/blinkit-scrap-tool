from __future__ import annotations

from app.domain.models import chunk_queries


def test_chunk_queries_seven_by_two_locations() -> None:
    """7 keywords × 2 locations with size 6 → 4 jobs (2 chunks × 2 locations)."""
    queries = [f"q{i}" for i in range(7)]
    chunks = chunk_queries(queries, 6)
    assert len(chunks) == 2
    assert len(chunks[0]) == 6
    assert len(chunks[1]) == 1

    locations = 2
    jobs_total = locations * len(chunks)
    assert jobs_total == 4


def test_chunk_queries_rejects_invalid_size() -> None:
    try:
        chunk_queries(["a"], 0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
