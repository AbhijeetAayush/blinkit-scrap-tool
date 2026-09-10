from __future__ import annotations


class DomainError(Exception):
    """Base domain error."""


class AuthError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class ParseEmptyError(DomainError):
    def __init__(self, message: str, html: str = "") -> None:
        super().__init__(message)
        self.html = html


class UnknownPlatformError(DomainError):
    pass
