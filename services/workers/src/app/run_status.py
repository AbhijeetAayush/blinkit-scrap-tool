"""Keep in sync with apps/web/lib/run-status.ts."""

TERMINAL_RUN_STATUSES = frozenset({"derived", "error", "budget", "halted"})


def is_run_terminal(status: str | None) -> bool:
    return bool(status and status in TERMINAL_RUN_STATUSES)
