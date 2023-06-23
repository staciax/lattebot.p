from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx.enums import Region
from valorantx.http import HTTPClient as _HTTPClient, Route

from .auth import RiotAuth

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop

    from valorantx.http import Response

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
