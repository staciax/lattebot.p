from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.app_commands import Command, ContextMenu
from discord.ext import commands
from dotenv import load_dotenv

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__name__)


class Stats(commands.Cog, name='stats'):
    """Stats cog"""

    def __init__(self, bot: LatteMaid) -> None:
        load_dotenv()
        self.bot: LatteMaid = bot

    @commands.Cog.listener('on_app_command_completion')
    async def on_latte_app_command(
        self,
        interaction: discord.Interaction[LatteMaid],
        app_command: Command | ContextMenu,
    ) -> None:
        if self.bot.is_debug_mode():
            return

        if await self.bot.is_owner(interaction.user):
            return

        if self.bot.is_blocked(interaction.user):
            return

        command_type = app_command.type.value if isinstance(app_command, ContextMenu) else 1  # 1 is slash command
        channel = interaction.channel

        destination = None
        if interaction.guild is None:
            destination = 'Private Message'
            guild_id = None
        else:
            destination = f'#{channel} ({interaction.guild})'
            guild_id = interaction.guild.id

        _log.info(f'{interaction.created_at}: {interaction.user} in {destination}: /{app_command.qualified_name}')

        await self.bot.db.add_app_command(
            type=command_type,
            command=app_command.qualified_name,
            guild=guild_id,
            channel=interaction.channel_id,
            used=interaction.created_at,
            author=interaction.user.id,
            failed=interaction.command_failed,
        )


async def setup(bot: LatteMaid) -> None:
    await bot.add_cog(Stats(bot))
