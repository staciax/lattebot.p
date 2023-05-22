from __future__ import annotations

from typing import TYPE_CHECKING, Any, Coroutine, TypeVar

from valorantx import Region
from valorantx.http import HTTPClient as ValorantXHTTPClient, Route as ValorantXRoute

from .auth import RiotAuth

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop

    from .auth import RiotAuth
    from .types import account_henrikdev

    T = TypeVar('T')
    Response = Coroutine[Any, Any, T]

# fmt: off
__all__ = (
    'HTTPClient',
)
# fmt: on


class HTTPClient(ValorantXHTTPClient):
    if TYPE_CHECKING:
        _riot_auth: RiotAuth

    def __init__(self, loop: AbstractEventLoop) -> None:
        super().__init__(loop, region=Region.AP)  # default is AP
        self.riot_auth: RiotAuth = RiotAuth()

    async def build_headers(self) -> None:
        await self.__build_headers()

    def get_partial_account(self, name: str, tagline: str) -> Response[account_henrikdev.Response]:
        class HenrikRoute(ValorantXRoute):
            def __init__(self, method: str, path: str) -> None:
                self.method = method
                self.path = path
                self.url: str = 'https://api.henrikdev.xyz/valorant' + self.path

        route = HenrikRoute('GET', '/v1/account/{name}/{tagline}'.format(name=name, tagline=tagline))
        return self.request(route, headers={})
