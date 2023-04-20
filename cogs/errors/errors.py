from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.app_commands import AppCommandError
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__file__)


class Errors(commands.Cog, name='errors'):
    """Developer commands"""

    def __init__(self, bot: LatteMaid) -> None:
        self.bot = bot

    @commands.Cog.listener('on_app_command_error')
    async def on_app_command_error(self, interaction: discord.Interaction[LatteMaid], error: AppCommandError) -> None:
        print(error)

    @commands.Cog.listener('on_view_error')
    async def on_view_error(self, interaction: discord.Interaction[LatteMaid], error: Exception, item: discord.ui.Item) -> None:
        print(error)

    @commands.Cog.listener('on_modal_error')
    async def on_modal_error(self, interaction: discord.Interaction[LatteMaid], error: Exception, modal: discord.ui.Modal) -> None:
        print(error)
