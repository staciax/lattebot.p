from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands.translator import locale_str as _T

from core.checks import owner_only
from core.i18n import I18n

from .abc import MixinMeta

if TYPE_CHECKING:
    from core.bot import LatteMaid

SUPPORT_GUILD_ID = 1097859504906965042

_log = logging.getLogger(__name__)
_ = I18n('valorant.admin', __file__, read_only=True)


class Admin(MixinMeta):
    @app_commands.command(name=_T('run_valorant'), description=_T('Run valorant client'))  # type: ignore
    @app_commands.guilds(SUPPORT_GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    @owner_only()
    async def run_valorant(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.bot.run_valorant_client()
        await interaction.followup.send(_('run_valorant', interaction.locale))
