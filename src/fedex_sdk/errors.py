from __future__ import annotations

from typing import Any, Mapping, Optional


class FedExError(Exception):
    """Base exception for this package."""


class FedExAPIError(FedExError):
    """Raised when FedEx returns a non-success HTTP response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        transaction_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response
        self.headers = headers or {}
        self.transaction_id = transaction_id


class FedExAuthenticationError(FedExAPIError):
    """Raised for authentication and authorization failures."""


class FedExRateLimitError(FedExAPIError):
    """Raised when FedEx rate limits the request."""


class FedExValidationError(FedExAPIError):
    """Raised for request validation failures."""
