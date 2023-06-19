from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union

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
        self, interaction: discord.Interaction[LatteMaid], app_command: Union[Command, ContextMenu]
    ) -> None:
        ...
        # if interaction.user == self.bot.owner:
        #     return
        # command = app_command.qualified_name
        # message = interaction.message
        # channel = interaction.channel
        # assert message is not None
        # assert channel is not None

        # destination = None
        # if interaction.guild is None:
        #     destination = 'Private Message'
        #     guild_id = None
        # else:
        #     destination = f'#{channel} ({interaction.guild})'
        #     guild_id = interaction.guild.id
        # if interaction.command:
        #     content = f'/{interaction.command.qualified_name}'
        # else:
        #     content = message.content
        # assert message is not None
        # _log.info(f'{message.created_at}: {message.author} in {destination}: {content}')
        # await self.bot.db.create_app_command(
        #     guild=guild_id,
        #     command=command,
        #     channel=channel.id,
        #     author=interaction.user.id,
        #     used=interaction.created_at,
        #     failed=False,
        # )


async def setup(bot: LatteMaid) -> None:
    await bot.add_cog(Stats(bot))
