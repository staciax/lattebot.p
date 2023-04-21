from __future__ import annotations

from typing import TYPE_CHECKING, Any, Coroutine, TypeVar

from valorantx2.http import HTTPClient as ValorantXHTTPClient, Route as ValorantXRoute

if TYPE_CHECKING:
    from .types import account_henrikdev

    T = TypeVar('T')
    Response = Coroutine[Any, Any, T]

# fmt: off
__all__ = (
    'HTTPClient',
)
# fmt: on


class HTTPClient(ValorantXHTTPClient):
    def get_partial_account(self, name: str, tagline: str) -> Response[account_henrikdev.Response]:
        class HenrikRoute(ValorantXRoute):
            def __init__(self, method: str, path: str) -> None:
                self.method = method
                self.path = path
                self.url: str = 'https://api.henrikdev.xyz/valorant' + self.path

        route = HenrikRoute('GET', '/v1/account/{name}/{tagline}'.format(name=name, tagline=tagline))
        return self.request(route, headers={})
