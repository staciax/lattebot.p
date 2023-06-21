from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

import aiohttp
import yarl
from valorantx import RiotAuth as RiotAuth_
from valorantx.errors import RiotAuthenticationError
from valorantx.utils import MISSING

from .errors import RiotAuthRateLimitedError

if TYPE_CHECKING:
    from typing_extensions import Self

    from core.bot import LatteMaid
    from core.utils.database.models.riot_account import RiotAccount as RiotAccountDB

# fmt: off
__all__ = (
    'RiotAuth',
)
# fmt: on

_log = logging.getLogger(__name__)


class RiotAuth(RiotAuth_):
    RIOT_CLIENT_USER_AGENT = 'RiotClient/66.0.2.5148951.1064 %s (Windows;10;;Professional, x64)'

    def __init__(self) -> None:
        super().__init__()
        self.owner_id: Optional[int] = None
        self.bot: LatteMaid = MISSING
        self.session_is_outdated: bool = False

    def __hash__(self) -> int:
        return hash((self.owner_id, self.user_id, self.region))  # self.expires_at

    async def authorize(
        self, username: str, password: str, use_query_response_mode: bool = False, remember: bool = False
    ) -> None:
        try:
            await super().authorize(username, password, use_query_response_mode, remember)
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                if e.headers is not None:
                    retry_after = e.headers.get('Retry-After')
                    if retry_after and int(retry_after) >= 0:
                        raise RiotAuthRateLimitedError(int(retry_after))

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
        self.owner_id = data.owner_id
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

    async def reauthorize(self) -> None:
        _log.info(f're authorizing {self.game_name}#{self.tag_line}({self.puuid})')

        if self.session_is_outdated:
            raise RuntimeError(f'failed to re authorize {self.game_name}#{self.tag_line}({self.puuid})')

        for tries in range(4):
            try:
                await self.authorize('', '')
            except RiotAuthenticationError as e:
                _log.info(f'failed status code: {e.status} message: {e.text}')
                if e.status == 403 and tries <= 1:  # 403 Forbidden
                    if self.bot is not MISSING:
                        # self.bot.dispatch('re_authorize_forbidden', RiotAuth.RIOT_CLIENT_USER_AGENT)
                        version = await self.bot.valorant_client.valorant_api.fetch_version()
                        RiotAuth.RIOT_CLIENT_USER_AGENT = (
                            f'RiotClient/{version.riot_client_build} %s (Windows;10;;Professional, x64)'
                        )
                    await asyncio.sleep(1)
                    continue
                elif e.status == 400 and tries <= 2:
                    continue
                else:
                    raise e
            else:
                if self.bot is not MISSING:
                    self.bot.dispatch('re_authorized_successfully', self)
                _log.info(f'successfully re authorized {self.game_name}#{self.tag_line}({self.puuid})')
                break
        else:
            self.session_is_outdated = True
            self.bot.dispatch('re_authorize_failed', self)
            raise RuntimeError(f'failed to re authorize {self.game_name}#{self.tag_line}({self.puuid})')
