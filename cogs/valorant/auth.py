from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from valorantx.errors import RiotAuthenticationError
from valorantx.utils import MISSING

from valorantx2.auth import RiotAuth as RiotAuth_

if TYPE_CHECKING:
    from typing_extensions import Self

    from core.bot import LatteMaid

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
        self.bot: LatteMaid = MISSING
        self.session_is_outdated: bool = False

    def __hash__(self) -> int:
        return hash((self.owner_id, self.user_id, self.region))  # self.expires_at

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

    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> Self:
        self = super().from_data(data)
        if 'owner_id' in data:
            self.owner_id = data['owner_id']
        return self
