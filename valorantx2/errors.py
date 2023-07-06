from typing import Any

from aiohttp import ClientResponse
from valorantx.errors import (
    BadRequest as BadRequest,
    Forbidden as Forbidden,
    HTTPException as HTTPException,
    InGameAPIError as InGameAPIError,
    InternalServerError as InternalServerError,
    NotFound as NotFound,
    RateLimited as RateLimited,
    RiotAuthenticationError as RiotAuthenticationError,
    RiotAuthError as RiotAuthError,
    RiotAuthRequired as RiotAuthRequired,
    RiotMultifactorError as RiotMultifactorError,
    RiotRatelimitError as RiotRatelimitError,
    RiotUnknownErrorTypeError as RiotUnknownErrorTypeError,
    RiotUnknownResponseTypeError as RiotUnknownResponseTypeError,
    ValorantXError as ValorantXError,
)

__all__ = (
    'ValorantXError',
    'HTTPException',
    'InGameAPIError',
    'BadRequest',
    'NotFound',
    'InternalServerError',
    'Forbidden',
    'RateLimited',
    'RiotAuthRequired',
    'RiotAuthError',
    'RiotAuthenticationError',
    'RiotRatelimitError',
    'RiotMultifactorError',
    'RiotUnknownResponseTypeError',
    'RiotUnknownErrorTypeError',
)


class RiotAuthRateLimitedError(ValorantXError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after: int = retry_after
        super().__init__(f'Rate limited. Retry after {retry_after} seconds.')


class RiotAuthMultiFactorInvalidCode(RiotAuthError):
    """Raised when a user has reached the max limit of Riot accounts."""

    def __init__(self, response: ClientResponse, message: str | dict[str, Any] | None, mfa_code: str) -> None:
        self.mfa_code: str = mfa_code
        super().__init__(response, message)
