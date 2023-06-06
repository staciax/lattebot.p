from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, List, Literal

import discord
from discord import app_commands

# i18n
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import dynamic_cooldown
from discord.ext import tasks

from core.checks import cooldown_short

from .abc import MixinMeta

if TYPE_CHECKING:
    from core.bot import LatteMaid


_log = logging.getLogger(__name__)


class Notify(MixinMeta):
    async def send_notify(self):
        ...  # todo webhook send

    @tasks.loop(time=time(hour=0, minute=1, second=00))  # utc 00:01:00
    async def notify_alert(self) -> None:
        await self.send_notify()

    @notify_alert.before_loop
    async def before_daily_send(self) -> None:
        await self.bot.wait_until_ready()
        await self.valorant_client.wait_until_ready()
        _log.info('Notify alert loop started')

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
