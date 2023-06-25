from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from valorantx.enums import Region
from valorantx.http import HTTPClient as _HTTPClient, Route

from .auth import RiotAuth

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop

    from valorantx.http import Response
    from valorantx.types import store

    from .auth import RiotAuth
    from .types import account_henrikdev


# fmt: off
__all__ = (
    'HTTPClient',
)
# fmt: on


class HTTPClient(_HTTPClient):
    def __init__(self, loop: AbstractEventLoop) -> None:
        super().__init__(loop, region=Region.AsiaPacific)  # default is AsiaPacific
        self.riot_auth: RiotAuth = RiotAuth()  # set riot auth to default

    async def re_build_headers(self) -> None:
        self._puuid = self.riot_auth.puuid
        await self.__build_headers()

    def get_partial_account(self, game_name: str, tag_line: str) -> Response[account_henrikdev.Response]:
        r = Route.from_url(
            'GET',
            'https://api.henrikdev.xyz/valorant/v1/account/{game_name}/{tag_line}',
            game_name=game_name,
            tag_line=tag_line,
        )
        return self.request(r, headers={})

    # test

    def build_headers(self, riot_auth: RiotAuth) -> Dict[str, str]:
        headers = {
            'Authorization': 'Bearer %s' % riot_auth.access_token,
            'X-Riot-Entitlements-JWT': riot_auth.entitlements_token,
            'X-Riot-ClientPlatform': HTTPClient.RIOT_CLIENT_PLATFORM,
            'X-Riot-ClientVersion': HTTPClient.RIOT_CLIENT_VERSION,
        }
        return headers

    def get_store_storefront_test(self, riot_auth: RiotAuth) -> Response[store.StoreFront]:
        headers = self.build_headers(riot_auth)
        region = Region(riot_auth.region) if riot_auth.region is not None else self.region
        return self.request(
            Route('GET', '/store/v2/storefront/{puuid}', region, puuid=riot_auth.puuid),
            headers=headers,
        )
