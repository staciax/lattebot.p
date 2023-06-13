from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.app_commands import AppCommandError
from discord.ext import commands
from valorantx.errors import BadRequest

from core.translator import _

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__file__)


class Errors(commands.Cog, name='errors'):
    """Developer commands"""

    def __init__(self, bot: LatteMaid) -> None:
        self.bot = bot

    def _log_error(self, interaction: discord.Interaction[LatteMaid], error: Exception) -> None:
        command = interaction.command
        if command is not None:
            if command._has_any_error_handlers():
                return

            _log.error('Ignoring exception in command %r', command.name, exc_info=error)
        else:
            _log.error('Ignoring exception ', exc_info=error)

    @commands.Cog.listener('on_app_command_error')
    async def on_app_command_error(self, interaction: discord.Interaction[LatteMaid], error: AppCommandError) -> None:
        self._log_error(interaction, error)
        if isinstance(error, BadRequest):
            await interaction.followup.send(error.text, ephemeral=True, silent=True)

    @commands.Cog.listener('on_view_error')
    async def on_view_error(
        self, interaction: discord.Interaction[LatteMaid], error: Exception, item: discord.ui.Item
    ) -> None:
        print('extras', interaction.extras)
        print('command', interaction.command)
        self._log_error(interaction, error)
        if isinstance(error, BadRequest):
            await interaction.followup.send(error.text, ephemeral=True, silent=True)

    @commands.Cog.listener('on_modal_error')
    async def on_modal_error(
        self, interaction: discord.Interaction[LatteMaid], error: Exception, modal: discord.ui.Modal
    ) -> None:
        self._log_error(interaction, error)
        await interaction.response.send_message(_('Oops! Something went wrong.'), ephemeral=True)
