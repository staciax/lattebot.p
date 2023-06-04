from __future__ import annotations

from typing import TYPE_CHECKING, Any, Coroutine, Optional, TypeVar

from valorantx import Region
from valorantx.http import HTTPClient as ValorantXHTTPClient, Route as ValorantXRoute

from .auth import RiotAuth

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop

    from valorantx.types import store

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
        riot_auth: RiotAuth

    def __init__(self, loop: AbstractEventLoop) -> None:
        super().__init__(loop, region=Region.AsiaPacific)  # default is AsiaPacific
        self.riot_auth: RiotAuth = RiotAuth()

    async def re_build_headers(self) -> None:
        self._puuid = self.riot_auth.puuid
        await self.__build_headers()

    def get_partial_account(self, game_name: str, tag_line: str) -> Response[account_henrikdev.Response]:
        r = ValorantXRoute.from_url(
            'GET',
            'https://api.henrikdev.xyz/valorant/v1/account/{game_name}/{tag_line}',
            game_name=game_name,
            tag_line=tag_line,
        )
        return self.request(r, headers={})

    def get_store_storefront(self, puuid: Optional[str] = None) -> Response[store.StoreFront]:
        puuid = puuid or self.puuid
        # headers = {}
        return self.request(ValorantXRoute('GET', '/store/v2/storefront/{puuid}', self.region, puuid=self.puuid))
