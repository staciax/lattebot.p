from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.app_commands.translator import locale_str as _T
from dotenv import load_dotenv

import valorantx2 as valorantx
from core.checks import owner_only
from core.i18n import I18n

from .abc import MixinMeta

if TYPE_CHECKING:
    from core.bot import LatteMaid


_log = logging.getLogger(__name__)
_ = I18n('valorant.admin', __file__, read_only=True)

SUPPORT_GUILD_ID = 1097859504906965042


class Admin(MixinMeta):
    load_dotenv()

    vcm = app_commands.Group(
        name=_T('valorant'),
        description=_T('Valorant client manager'),
        guild_ids=[SUPPORT_GUILD_ID],
        default_permissions=discord.Permissions(
            administrator=True,
        ),
    )

    @vcm.command(name=_T('run'), description=_T('Run valorant client'))  # type: ignore
    @app_commands.describe(username='Riot account username', password='Riot account password')
    @owner_only()
    async def valorant_run(
        self,
        interaction: discord.Interaction[LatteMaid],
        username: Optional[str],
        password: Optional[str],
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        username = username or os.getenv('RIOT_USERNAME')
        password = password or os.getenv('RIOT_PASSWORD')

        if username is None or password is None:
            await interaction.followup.send(
                _('valorant client is not initialized due to missing credentials.', interaction.locale)
            )
            return

        try:
            await self.valorant_client.authorize(username, password)
        except valorantx.RiotAuthenticationError as e:
            _log.error(f'valorant client failed to authorized', exc_info=e)
            raise e
        else:
            _log.info('valorant client is initialized.')

        await interaction.followup.send('successfully initialized valorant client.', silent=True)

    @vcm.command(name=_T('close'), description=_T('Close valorant client'))  # type: ignore
    @owner_only()
    async def valorant_close(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            await self.valorant_client.close()
        finally:
            _log.info('valorant client is closed.')

        await interaction.followup.send('successfully closed valorant client.', silent=True)

    @vcm.command(name=_T('clear'), description=_T('Clear valorant client'))  # type: ignore
    @owner_only()
    async def valorant_clear(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            self.valorant_client.clear()
        finally:
            _log.info('valorant client is cleared.')

        await interaction.followup.send('successfully cleared valorant client.', silent=True)

    @vcm.command(name=_T('cache_clear'), description=_T('Clear valorant client cache'))  # type: ignore
    @owner_only()
    async def valorant_cache_clear(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            await self.valorant_client.cache_clear()
        finally:
            _log.info('valorant client cache is cleared.')

        await interaction.followup.send('successfully cleared valorant client cache.', silent=True)
