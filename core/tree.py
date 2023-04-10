from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, List, Optional

import discord
from discord import app_commands

if TYPE_CHECKING:
    from .bot import LatteMaid

_log = logging.getLogger(__name__)

_ = ...


class LatteMaidTree(app_commands.CommandTree['LatteMaid']):
    async def interaction_check(self, interaction: discord.Interaction[LatteMaid], /) -> bool:
        if await self.client.is_owner(interaction.user):
            return True

        if interaction.user.id in self.client.blacklist:
            await interaction.response.send_message(
                _('You are blacklisted from using this bot.'),
                ephemeral=True,
            )
            return False

        if interaction.client.is_maintenance():
            if interaction.type is discord.InteractionType.application_command:
                maintenance_time = interaction.client.maintenance_time
                if maintenance_time is not None:
                    remaining = datetime.datetime.now() - maintenance_time
                    await interaction.response.send_message(
                        _('This bot is currently in maintenance mode. It will be back at {time}.').format(
                            time=f'<t:{round(remaining.total_seconds())}:R>'
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        _('This bot is currently in maintenance mode.'),
                        ephemeral=True,
                    )
            return False

        return True

    async def sync(self, *, guild: Optional[discord.abc.Snowflake] = None) -> List[app_commands.AppCommand]:
        synced = await super().sync(guild=guild)
        if synced:
            _log.info('synced %s application commands %s' % (len(synced), f'for guild {guild.id}' if guild else ''))
        return synced

    async def on_error(
        self, interaction: discord.Interaction['LatteMaid'], error: app_commands.AppCommandError, /
    ) -> None:
        self.client.dispatch('app_command_error', interaction, error)
        # return await interaction_error_handler(interaction, error)
