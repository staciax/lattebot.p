from __future__ import annotations

import asyncio
import logging
from datetime import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import dynamic_cooldown
from discord.ext import tasks

from core.checks import cooldown_short
from core.i18n import I18n
from valorantx2.errors import BadRequest, RateLimited

from .abc import MixinMeta
from .account_manager import AccountManager
from .features.notifications import NotifyView

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__name__)

_ = I18n('valorant.events', __file__, read_only=True)


class Notifications(MixinMeta):
    async def send_notify(self) -> None:
        ...

    async def do_notify_handle(self):
        async for user in self.bot.db.fetch_users():
            if len(user.riot_accounts) <= 0:
                continue

            if user.notification_settings is not None:
                if not user.notification_settings.is_enabled():
                    continue

                if user.notification_settings.is_empty():
                    continue

            account_manager = AccountManager(user, self.bot)
            await account_manager.wait_until_ready()

            # for riot_auth in account_manager.riot_accounts:
            #     try:
            #         sf = self.valorant_client.fetch_storefront(riot_auth)
            #     except BadRequest:
            #         # token expired
            #         continue
            #     except RateLimited:
            #         # await asyncio.sleep(e.retry_after)  # TODO: retry_after in RateLimited
            #         await asyncio.sleep(60 * 5)  # 5 minutes
            #     else:
            #         await self.send_notify()
            #         # TODO: send webhook

    @tasks.loop(time=time(hour=0, minute=1, second=00))  # utc 00:01:00
    async def notify_alert(self) -> None:
        ...
        # await self.do_notify()

    @notify_alert.before_loop
    async def before_daily_send(self) -> None:
        await self.bot.wait_until_ready()
        if not self.valorant_client.is_ready():
            return
        _log.info('notify alert loop started')

    @app_commands.command(
        name=_T('notify'),
        description=_T('Setting notification'),
    )  # type: ignore
    @dynamic_cooldown(cooldown_short)
    async def notify(self, interaction: discord.Interaction[LatteMaid]) -> None:
        """Setting notification"""
        view = NotifyView(interaction)
        await view.start()
