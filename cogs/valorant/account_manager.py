from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

from core.database.models import User as UserDB
from core.i18n import I18n
from valorantx2.utils import MISSING

from .auth import RiotAuth

if TYPE_CHECKING:
    from core.bot import LatteMaid

_ = I18n('valorant.account_manager', __file__, read_only=True)


class AccountManager:
    def __init__(
        self,
        user: UserDB,
        bot: LatteMaid = MISSING,
        *,
        re_authorize: bool = True,
        init_later: bool = True,
    ) -> None:
        self.author: UserDB = user
        self.bot: LatteMaid = bot
        self.re_authorize: bool = re_authorize
        self.main_account: RiotAuth | None = None
        self._accounts: dict[str, RiotAuth] = {}
        self._hide_display_name: bool = False
        self._ready: asyncio.Event = asyncio.Event()
        if init_later:
            self.bot.loop.create_task(self._init())

    def __repr__(self) -> str:
        return f'<AccountManager author={self.author!r}>'

    def __hash__(self) -> int:
        return hash(self.author)

    def __len__(self) -> int:
        return len(self._accounts)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AccountManager) and self.author == other.author

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    async def _init(self) -> None:
        for riot_account in sorted(self.author.riot_accounts, key=lambda x: x.created_at):
            riot_auth = RiotAuth.from_database(riot_account)

            # for dispatching events to the bot when reauthorizing
            if self.bot is not MISSING:
                riot_auth.bot = self.bot

            if self.re_authorize and time.time() > riot_auth.expires_at:
                with contextlib.suppress(Exception):
                    await riot_auth.reauthorize()

                # if not riot_auth.is_available():
                #     _log.warning(f'failed to authorize {riot_auth.game_name}#{riot_auth.tag_line}({riot_auth.puuid})')
                #     continue

            self._accounts[riot_auth.puuid] = riot_auth
            # if self.author.main_riot_account_id == riot_account.id:
            #     self.main_account = riot_auth

        self._ready.set()

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    @property
    def hide_display_name(self) -> bool:
        return self._hide_display_name

    @property
    def accounts(self) -> list[RiotAuth]:
        return list(self._accounts.values())

    def is_ready(self) -> bool:
        return self._ready.is_set()

    def get_account(self, puuid: str, /) -> RiotAuth | None:
        return self._accounts.get(puuid)

    async def add_account(self, riot_auth: RiotAuth, /) -> None:
        await self.bot.db.add_riot_account(
            self.author.id,
            puuid=riot_auth.puuid,
            game_name=riot_auth.game_name,
            tag_line=riot_auth.tag_line,
            region=riot_auth.region or 'ap',
            scope=riot_auth.scope,  # type: ignore
            token_type=riot_auth.token_type,  # type: ignore
            expires_at=riot_auth.expires_at,
            id_token=riot_auth.id_token,  # type: ignore
            access_token=riot_auth.access_token,  # type: ignore
            entitlements_token=riot_auth.entitlements_token,  # type: ignore
            ssid=riot_auth.get_ssid(),
            notify=False,
        )
        self._accounts[riot_auth.puuid] = riot_auth

    async def remove_account(self, puuid: str, /) -> None:
        await self.bot.db.remove_riot_account(puuid, self.author.id)

        try:
            self._accounts.pop(puuid)
        except KeyError:
            pass
