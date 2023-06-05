from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import aiohttp
import yarl
from valorantx import RiotAuth as RiotAuth_

if TYPE_CHECKING:
    from typing_extensions import Self

    from core.bot import LatteMaid
    from core.utils.database.models.riot_account import RiotAccount as RiotAccountDB

# fmt: off
__all__ = (
    'RiotAuth',
)
# fmt: on


class RiotAuth(RiotAuth_):
    def __init__(self) -> None:
        super().__init__()
        self.bot: Optional[LatteMaid] = None

    async def authorize_multi_factor(self, code: str, remember: bool = False):
        headers = {
            'Accept-Encoding': 'deflate, gzip, zstd',
            'user-agent': RiotAuth.RIOT_CLIENT_USER_AGENT % 'rso-auth',
            'Cache-Control': 'no-assets',
            'Accept': 'application/json',
        }

        data = {'type': 'multifactor', 'code': code, 'rememberDevice': remember}

        conn = aiohttp.TCPConnector(ssl=self._auth_ssl_ctx)
        async with aiohttp.ClientSession(
            connector=conn,
            raise_for_status=True,
            cookie_jar=self._cookie_jar,
        ) as session:
            async with session.put(
                'https://auth.riotgames.com/api/v1/authorization',
                json=data,
                ssl=self._auth_ssl_ctx,
                headers=headers,
            ) as resp:
                data = await resp.json()

            self._cookie_jar = session.cookie_jar
            self.__set_tokens_from_uri(data)

            # Get new entitlements token
            headers['Authorization'] = f'{self.token_type} {self.access_token}'
            async with session.post(
                'https://entitlements.auth.riotgames.com/api/token/v1',
                headers=headers,
                json={},
                # json={'urn': 'urn:entitlement:%'},
            ) as r:
                self.entitlements_token = (await r.json())['entitlements_token']

    @classmethod
    def from_db(cls, data: RiotAccountDB) -> Self:
        self = cls()
        self.id_token = data.id_token
        self.entitlements_token = data.entitlements_token
        self.access_token = data.access_token
        self.token_type = data.token_type
        self.expires_at = int(data.expires_at)
        self.user_id = data.puuid
        self.game_name = data.game_name
        self.tag_line = data.tag_line
        self.region = data.tag_line
        self._cookie_jar.update_cookies({'ssid': data.ssid}, yarl.URL('https://auth.riotgames.com'))
        return self

    def get_ssid(self) -> str:
        url = yarl.URL('https://auth.riotgames.com')
        riot_cookies = self._cookie_jar.filter_cookies(url)
        return riot_cookies['ssid'].value

    async def reauthorize(self) -> bool:
        if await super().reauthorize():
            if self.bot is not None:
                self.bot.dispatch('riot_account_update', self)
            return True
        return False
