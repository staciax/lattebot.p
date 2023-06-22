from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands.translator import locale_str as _T

import valorantx2 as valorantx
from core.checks import owner_only
from core.i18n import I18n

from .abc import MixinMeta

if TYPE_CHECKING:
    from core.bot import LatteMaid

SUPPORT_GUILD_ID = 1097859504906965042

_log = logging.getLogger(__name__)
_ = I18n('valorant.admin', __file__, read_only=True)


class Admin(MixinMeta):
    async def _run_valorant_client(self) -> None:
        try:
            await asyncio.wait_for(self.valorant_client.authorize('ragluxs', '4869_lucky'), timeout=60)
        except asyncio.TimeoutError:
            _log.error('valorant client failed to initialize within 60 seconds.')
        except valorantx.RiotAuthenticationError as e:
            await self.valorant_client._init()  # bypass the auth check
            _log.warning(f'valorant client failed to authorized', exc_info=e)
        else:
            _log.info('valorant client is initialized.')

    @app_commands.command(name=_T('run_valorant'), description=_T('Run valorant client'))  # type: ignore
    @app_commands.guilds(SUPPORT_GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    @owner_only()
    async def run_valorant(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await interaction.response.defer(ephemeral=True)
        await self._run_valorant_client()
        await interaction.followup.send(_('run_valorant', interaction.locale))
