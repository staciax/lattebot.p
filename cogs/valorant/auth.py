from __future__ import annotations

import asyncio
import logging
from secrets import token_urlsafe
from typing import TYPE_CHECKING

import aiohttp
import yarl
from valorantx.errors import RiotAuthenticationError
from valorantx.utils import MISSING

from valorantx2.auth import RiotAuth as RiotAuth_
from valorantx2.errors import RiotAuthRateLimitedError

if TYPE_CHECKING:
    from typing_extensions import Self

    from core.bot import LatteMaid
    from core.database.models import RiotAccount

# fmt: off
__all__ = (
    'RiotAuth',
)
# fmt: on

_log = logging.getLogger(__name__)


# https://github.com/floxay/python-riot-auth


class RiotAuth(RiotAuth_):
    RIOT_CLIENT_USER_AGENT = 'RiotClient/67.0.13.192.1064 %s (Windows;10;;Professional, x64)'

    def __init__(self) -> None:
        super().__init__()
        self.id: int | None = None
        self.display_name: str | None = None
        self.owner_id: int | None = None
        self.notify: bool = False
        self.bot: LatteMaid = MISSING
        self._is_available: bool = True

    def __hash__(self) -> int:
        return hash((self.owner_id, self.user_id, self.region))  # self.expires_at

    def is_available(self) -> bool:
        return self._is_available

    async def _authorize(
        self,
        username: str,
        password: str,
        use_query_response_mode: bool = False,
        remember: bool = False,
    ) -> bool:
        """
        Authenticate using username and password.
        """
        if username and password:
            self._cookie_jar.clear()

        conn = aiohttp.TCPConnector(ssl=self._auth_ssl_ctx)
        async with aiohttp.ClientSession(connector=conn, raise_for_status=True, cookie_jar=self._cookie_jar) as session:
            headers = {
                'Accept-Encoding': 'deflate, gzip, zstd',
                'user-agent': RiotAuth.RIOT_CLIENT_USER_AGENT % 'rso-auth',
                'Cache-Control': 'no-cache',
                'Accept': 'application/json',
            }

            # region Begin auth/Reauth
            body = {
                'acr_values': '',
                'claims': '',
                'client_id': 'riot-client',
                'code_challenge': '',
                'code_challenge_method': '',
                'nonce': token_urlsafe(16),
                'redirect_uri': 'http://localhost/redirect',
                'response_type': 'token id_token',
                'scope': 'openid link ban lol_region account',
            }
            if use_query_response_mode:
                body['response_mode'] = 'query'
            async with session.post(
                'https://auth.riotgames.com/api/v1/authorization',
                json=body,
                headers=headers,
            ) as r:
                data: dict = await r.json()
            # endregion

            body = {
                'language': 'en_US',
                'password': password,
                'region': None,
                'remember': remember,
                'type': 'auth',
                'username': username,
            }
            return await self.__fetch_access_token(session, body, headers, data)

    async def authorize(
        self,
        username: str,
        password: str,
        use_query_response_mode: bool = False,
        remember: bool = False,
    ) -> None:
        try:
            await self._authorize(username, password, use_query_response_mode, remember)
        except aiohttp.ClientResponseError as e:
            if e.headers is None:
                return
            if e.status == 429:
                retry_after = e.headers.get('Retry-After')
                if retry_after and int(retry_after) >= 0:
                    raise RiotAuthRateLimitedError(int(retry_after))

    async def reauthorize(self) -> None:
        _log.info(f're authorizing {self.game_name}#{self.tag_line}({self.puuid})')

        if not self.is_available():
            _log.debug(f'{self.game_name}#{self.tag_line}({self.puuid}) is not available')
            # TODO: something here
            return

        for tries in range(3):
            try:
                await self.authorize('', '')
            except RiotAuthenticationError as e:
                _log.info(f'failed status code: {e.status} message: {e.text}')
                if e.status == 403 and tries <= 1 and self.bot is not MISSING:
                    version = await self.bot.valorant_client.valorant_api.fetch_version()
                    RiotAuth.RIOT_CLIENT_USER_AGENT = (
                        f'RiotClient/{version.riot_client_build} %s (Windows;10;;Professional, x64)'
                    )
                    # self.bot.dispatch('valorant_version_updated', version)
                    await asyncio.sleep(1)
                    continue
                self._is_available = False
                raise e
            else:
                _log.info(f'successfully re authorized {self.game_name}#{self.tag_line}({self.puuid})')
                if self.bot is not MISSING:
                    self.bot.dispatch('re_authorized_successfully', self)
                break
        else:
            self._is_available = False
            self.bot.dispatch('re_authorize_failed', self)
            raise RuntimeError(
                f'failed to re authorize {self.game_name}#{self.tag_line}({self.puuid}) for user {self.owner_id}'
            )

    @classmethod
    def from_database(cls, riot_account: RiotAccount, /) -> Self:
        self = cls()
        self.id = riot_account.id
        self.owner_id = riot_account.owner_id
        self.display_name = riot_account.display_name
        self.access_token = riot_account.access_token
        self.id_token = riot_account.id_token
        self.entitlements_token = riot_account.entitlements_token
        self.token_type = riot_account.token_type
        self.expires_at = riot_account.expires_at
        self.user_id = riot_account.puuid
        self.game_name = riot_account.game_name
        self.tag_line = riot_account.tag_line
        self.region = riot_account.region
        self._cookie_jar.update_cookies({'ssid': riot_account.ssid}, yarl.URL('https://auth.riotgames.com'))
        return self
