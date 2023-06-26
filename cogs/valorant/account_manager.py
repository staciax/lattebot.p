from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING, Dict, List, Optional

from core.i18n import I18n
from core.utils.database.models import User
from valorantx2.utils import MISSING

from .auth import RiotAuth

if TYPE_CHECKING:
    from core.bot import LatteMaid

_ = I18n('valorant.account_manager', __file__, read_only=True)


class AccountManager:
    def __init__(self, user: User, bot: LatteMaid = MISSING) -> None:
        self.user: User = user
        self.bot: LatteMaid = bot
        self.main_account: Optional[RiotAuth] = None
        self._riot_accounts: Dict[str, RiotAuth] = {}
        self._hide_display_name: bool = False
        self._ready: asyncio.Event = asyncio.Event()
        self.bot.loop.create_task(self.init())

    def __repr__(self) -> str:
        return f'<AccountManager user={self.user!r}>'

    def __hash__(self) -> int:
        return hash(self.user)

    def __len__(self) -> int:
        return len(self._riot_accounts)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AccountManager) and self.user == other.user

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    async def init(self) -> None:
        for riot_account in sorted(self.user.riot_accounts, key=lambda x: x.created_at):
            # TODO: to_dict method
            payload = {
                'access_token': riot_account.access_token,
                'id_token': riot_account.id_token,
                'entitlements_token': riot_account.entitlements_token,
                'token_type': riot_account.token_type,
                'expires_at': riot_account.expires_at,
                'user_id': riot_account.puuid,
                'game_name': riot_account.game_name,
                'tag_line': riot_account.tag_line,
                'region': riot_account.region,
                'ssid': riot_account.ssid,
                'owner_id': riot_account.owner_id,
                'notify': riot_account.notify,
            }

            riot_auth = RiotAuth.from_data(payload)

            # for dispatching events to the bot when reauthorizing
            if self.bot is not MISSING:
                riot_auth.bot = self.bot

            if time.time() > riot_auth.expires_at:
                with contextlib.suppress(Exception):
                    await riot_auth.reauthorize()

            self._riot_accounts[riot_auth.puuid] = riot_auth
            if riot_account.main_account:
                self.main_account = riot_auth

        self._ready.set()

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    def get_riot_account(self, puuid: Optional[str]) -> Optional[RiotAuth]:
        return self._riot_accounts.get(puuid)  # type: ignore

    @property
    def hide_display_name(self) -> bool:
        return self._hide_display_name

    @property
    def riot_accounts(self) -> List[RiotAuth]:
        return list(self._riot_accounts.values())

    def is_ready(self) -> bool:
        return self._ready.is_set()
