from valorantx.errors import (
    AuthRequired as AuthRequired,
    BadRequest as BadRequest,
    Forbidden as Forbidden,
    HTTPException as HTTPException,
    InternalServerError as InternalServerError,
    NotFound as NotFound,
    RateLimited as RateLimited,
    RiotAuthenticationError as RiotAuthenticationError,
    RiotAuthError as RiotAuthError,
    RiotMultifactorError as RiotMultifactorError,
    RiotRatelimitError as RiotRatelimitError,
    RiotUnknownErrorTypeError as RiotUnknownErrorTypeError,
    RiotUnknownResponseTypeError as RiotUnknownResponseTypeError,
    ValorantAPIError as ValorantAPIError,
    ValorantXException as ValorantXException,
)

__all__ = (
    'ValorantXException',
    'ValorantAPIError',
    'HTTPException',
    'BadRequest',
    'NotFound',
    'InternalServerError',
    'Forbidden',
    'RateLimited',
    'AuthRequired',
    'RiotAuthError',
    'RiotAuthenticationError',
    'RiotRatelimitError',
    'RiotMultifactorError',
    'RiotUnknownResponseTypeError',
    'RiotUnknownErrorTypeError',
)


class RiotAuthRateLimitedError(ValorantXException):
    def __init__(self, retry_after: int) -> None:
        self.retry_after: int = retry_after
        super().__init__(f'Rate limited. Retry after {retry_after} seconds.')
