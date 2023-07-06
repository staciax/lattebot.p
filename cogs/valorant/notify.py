import asyncio
import logging
from datetime import datetime, time, timedelta

import discord
from discord import app_commands

# i18n
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import dynamic_cooldown
from discord.ext import tasks

from core.checks import cooldown_short
from core.i18n import I18n
from valorantx2.errors import BadRequest, RateLimited

from .abc import MixinMeta
from .account_manager import AccountManager

_log = logging.getLogger(__name__)

_ = I18n('valorant.events', __file__, read_only=True)


class Notify(MixinMeta):
    async def send_notify(self) -> None:
        ...

    async def do_notify(self):
        async for user in self.bot.db.get_users():
            if len(user.riot_accounts) <= 0:
                continue

            if user.notification_settings is not None:
                if not user.notification_settings.is_enabled():
                    continue

                if user.notification_settings.is_empty():
                    continue

            account_manager = AccountManager(user, self.bot)
            await account_manager.wait_until_ready()

            for riot_auth in account_manager.riot_accounts:
                try:
                    sf = self.valorant_client.fetch_storefront(riot_auth)
                except BadRequest:
                    # token expired
                    continue
                except RateLimited:
                    # await asyncio.sleep(e.retry_after)  # TODO: retry_after in RateLimited
                    await asyncio.sleep(60 * 5)  # 5 minutes
                else:
                    await self.send_notify()
                    # TODO: send webhook

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

    # notify = app_commands.Group(name=_T('notify'), description=_T('Notify commands'), guild_only=True)

    # @notify.command(
    #     name=_T('add'),
    #     description=_T('Set a notification when a specific skin is available on your store'),
    # )  # type: ignore
    # @app_commands.describe(skin=_T('The name of the skin you want to notify'))
    # @app_commands.rename(skin=_T('skin'))
    # @dynamic_cooldown(cooldown_short)
    # async def notify_add(self, interaction: discord.Interaction[LatteMaid], skin: str) -> None:
    #     """Set a notification when a specific skin is available on your store"""
    #     ...

    # @notify_add.autocomplete('skin')  # type: ignore
    # async def notify_add_autocomplete(
    #     self, interaction: discord.Interaction[LatteMaid], current: str
    # ) -> List[app_commands.Choice[str]]:
    #     ...

    # @notify.command(
    #     name=_T('list'),
    #     description=_T('View skins you have set a for notification.'),
    # )  # type: ignore
    # @dynamic_cooldown(cooldown_short)
    # async def notify_list(self, interaction: discord.Interaction[LatteMaid]) -> None:
    #     """View skins you have set a notification for"""
    #     ...

    # @notify.command(
    #     name=_T('mode'),
    #     description=_T('Change notification mode'),
    # )  # type: ignore
    # @app_commands.describe(mode=_T('Choose notification'))
    # @app_commands.choices(
    #     mode=[
    #         app_commands.Choice(name=_T('Specified Skin'), value=1),
    #         app_commands.Choice(name=_T('All Skin'), value=2),
    #         app_commands.Choice(name=_T('Off'), value=0),
    #     ]
    # )
    # @app_commands.rename(mode=_T('mode'))
    # @dynamic_cooldown(cooldown_short)
    # async def notify_mode(self, interaction: discord.Interaction[LatteMaid], mode: app_commands.Choice[int]) -> None:
    #     """Set Skin Notifications mode"""
    #     ...

    # @notify.command(name=_T('test'))  # type: ignore
    # @dynamic_cooldown(cooldown_short)
    # async def notify_test(self, interaction: discord.Interaction[LatteMaid]) -> None:
    #     """Test Notifications"""
    #     ...
