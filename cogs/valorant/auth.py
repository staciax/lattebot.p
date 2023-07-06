from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

import yarl
from valorantx.errors import RiotAuthenticationError
from valorantx.utils import MISSING

from valorantx2.auth import RiotAuth as RiotAuth_

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
    RIOT_CLIENT_USER_AGENT = 'RiotClient/67.0.0.5150528.1064 %s (Windows;10;;Professional, x64)'

    def __init__(self) -> None:
        super().__init__()
        self.owner_id: Optional[int] = None
        self.notify: bool = False
        self.bot: LatteMaid = MISSING
        self._is_available: bool = True

    def __hash__(self) -> int:
        return hash((self.owner_id, self.user_id, self.region))  # self.expires_at

    def is_available(self) -> bool:
        return self._is_available

    async def reauthorize(self) -> None:
        _log.info(f're authorizing {self.game_name}#{self.tag_line}({self.puuid})')

        if not self.is_available():
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
            self._is_available = False
            self.bot.dispatch('re_authorize_failed', self)
            raise RuntimeError(f'failed to re authorize {self.game_name}#{self.tag_line}({self.puuid})')

    @classmethod
    def from_database(cls, riot_account: RiotAccount, /) -> Self:
        self = cls()
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
