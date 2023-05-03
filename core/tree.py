from __future__ import annotations

# import datetime
import logging
from typing import TYPE_CHECKING, List, Optional

import discord
from discord import app_commands

if TYPE_CHECKING:
    from .bot import LatteMaid

_log = logging.getLogger('lattemaid.' + __name__)

_ = ...


class LatteMaidTree(app_commands.CommandTree['LatteMaid']):
    async def interaction_check(self, interaction: discord.Interaction[LatteMaid], /) -> bool:
        if await self.client.is_owner(interaction.user):
            return True

        user_id = interaction.user.id
        # guild_id = interaction.guild.id if interaction.guild is not None else None

        # TODO: spam check

        # if user_id in self.client.db.blacklist:
        #     await interaction.response.send_message(
        #         _('You are blacklisted from using this bot.'),
        #         ephemeral=True,
        #     )
        #     return False

        # if guild_id is not None and guild_id in self.client.db.blacklist:
        #     await interaction.response.send_message(
        #         _('This guild is blacklisted from using this bot.'),
        #         ephemeral=True,
        #     )
        #     return False

        # if interaction.client.is_maintenance():
        #     if interaction.type is discord.InteractionType.application_command:
        #         maintenance_time = interaction.client.maintenance_time
        #         if maintenance_time is not None:
        #             remaining = datetime.datetime.now() - maintenance_time
        #             await interaction.response.send_message(
        #                 _('This bot is currently in maintenance mode. It will be back at {time}.').format(
        #                     time=f'<t:{round(remaining.total_seconds())}:R>'
        #                 ),
        #                 ephemeral=True,
        #             )
        #         else:
        #             await interaction.response.send_message(
        #                 _('This bot is currently in maintenance mode.'),
        #                 ephemeral=True,
        #             )
        #     return False

        if interaction.type is discord.InteractionType.application_command:
            user_db = await self.client.db.get_user(user_id)
            if user_db is not None and user_db not in self.client.db.users:
                self.client.loop.create_task(self.client.db.create_user(id=user_id, locale=interaction.locale.value))
            elif user_db is not None and user_db.locale != interaction.locale.value:
                self.client.loop.create_task(self.client.db.update_user(id=user_id, locale=interaction.locale.value))
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
