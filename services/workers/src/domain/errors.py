class AppError(Exception):
    """Base error for workers."""


class ParseEmptyError(AppError):
    """Unlocker returned a page with zero product cards."""

    def __init__(self, message: str, html: str = "") -> None:
        super().__init__(message)
        self.html = html


class UnlockerBlockedError(AppError):
    """Unlocker or target returned a block / challenge page."""


class UnserviceableError(AppError):
    """Location is outside the platform delivery footprint."""


class BudgetExceededError(AppError):
    """Daily unlocker credit budget exhausted."""


class SignatureError(AppError):
    """QStash JWT verification failed."""


class UnknownPlatformError(AppError):
    """No PlatformCatalog registered for the given platform id."""
