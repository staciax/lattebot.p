import logging

import aiohttp
import yarl
from valorantx import RiotAuth as RiotAuth_

from .errors import RiotAuthMultiFactorInvalidCode, RiotAuthRateLimitedError, RiotUnknownResponseTypeError

# fmt: off
__all__ = (
    'RiotAuth',
)
# fmt: on

_log = logging.getLogger(__name__)


# https://github.com/floxay/python-riot-auth


class RiotAuth(RiotAuth_):
    RIOT_CLIENT_USER_AGENT = 'RiotClient/67.0.0.5150528.1064 %s (Windows;10;;Professional, x64)'

    async def authorize(
        self,
        username: str,
        password: str,
        use_query_response_mode: bool = False,
        remember: bool = False,
    ) -> None:
        try:
            await super().authorize(username, password, use_query_response_mode, remember)
        except aiohttp.ClientResponseError as e:
            if e.headers is None:
                return
            if e.status == 429:
                retry_after = e.headers.get('Retry-After')
                if retry_after and int(retry_after) >= 0:
                    raise RiotAuthRateLimitedError(int(retry_after))

    async def authorize_multi_factor(self, code: str, remember: bool = False) -> None:
        # TODO: multi_factor rate limit error handling
        await self._authorize_multi_factor(code, remember)

    async def _authorize_multi_factor(self, code: str, remember: bool = False):
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
                resp_type = data['type']
                if resp_type == 'response':
                    ...
                elif resp_type == 'multifactor':
                    raise RiotAuthMultiFactorInvalidCode(resp, 'The code you entered is invalid.', code)
                else:
                    raise RiotUnknownResponseTypeError(
                        resp, f'Got unknown response type `{resp_type}` during authentication.'
                    )

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

    def get_ssid(self) -> str:
        url = yarl.URL('https://auth.riotgames.com')
        riot_cookies = self._cookie_jar.filter_cookies(url)
        if 'ssid' not in riot_cookies:
            return ''
        return riot_cookies['ssid'].value
