from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING, Dict, List, Optional

from core.translator import _
from core.utils.database.models import User
from valorantx2.auth import RiotAuth
from valorantx2.utils import MISSING

if TYPE_CHECKING:
    from core.bot import LatteMaid


class AccountManager:
    def __init__(self, user: User, bot: LatteMaid = MISSING) -> None:
        self.user: User = user
        self.bot: LatteMaid = bot
        self.first_account: Optional[RiotAuth] = None
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
        for index, riot_account in enumerate(sorted(self.user.riot_accounts, key=lambda x: x.created_at)):
            riot_auth = RiotAuth.from_db(riot_account)

            # for dispatching events to the bot when reauthorizing
            if self.bot is not MISSING:
                riot_auth.bot = self.bot

            if time.time() > riot_auth.expires_at:
                with contextlib.suppress(Exception):
                    await riot_auth.reauthorize()

            self._riot_accounts[riot_auth.puuid] = riot_auth
            if index == 0:
                self.first_account = riot_auth

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
