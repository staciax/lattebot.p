from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

import discord
from discord import app_commands

if TYPE_CHECKING:
    from .bot import LatteMaid


_log = logging.getLogger(__name__)


class LatteMaidTree(app_commands.CommandTree['LatteMaid']):
    async def interaction_check(self, interaction: discord.Interaction[LatteMaid], /) -> bool:
        user = interaction.user
        guild = interaction.guild
        locale = interaction.locale

        if await self.client.is_owner(user):
            return True

        # TODO: spam check

        if guild and self.client.is_blocked(guild):
            _log.info('guild %s is blacklisted', guild.id)

            await interaction.response.send_message(
                # _('This guild is blacklisted from using this bot.'),
                'This guild is blacklisted from using this bot.',
                ephemeral=True,
            )

            try:
                await guild.leave()
            except discord.HTTPException:
                _log.exception('failed to leave guild %s', guild.id)
            else:
                _log.info('left guild %s', guild.id)

            return False

        if user and self.client.is_blocked(user):
            _log.info('blacklisted user tried to use bot %s', user)

            await interaction.response.send_message(
                'You are blacklisted from using this bot.',
                ephemeral=True,
            )

            # remove user from database
            if _ := await self.client.db.get_user(user.id):
                self.client.loop.create_task(self.client.db.delete_user(user.id))

            return False

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

        # if interaction.type is discord.InteractionType.application_command:
        if isinstance(interaction.command, app_commands.Command) and interaction.user:  # TODO: context menu support
            user_db = await self.client.db.get_user(interaction.user.id)
            if user_db is None:
                await self.client.db.create_user(interaction.user.id, locale=locale.value)
                # self.client.loop.create_task(self.client.db.create_user(user_id, locale=interaction.locale.value))
            elif user_db.locale != interaction.locale.value:
                self.client.loop.create_task(self.client.db.update_user(interaction.user.id, locale=locale.value))

        return True

    async def sync(self, *, guild: Optional[discord.abc.Snowflake] = None) -> List[app_commands.AppCommand]:
        synced = await super().sync(guild=guild)
        if synced:
            _log.info('synced %s application commands %s' % (len(synced), f'for guild {guild.id}' if guild else ''))
        return synced

    async def on_error(
        self,
        interaction: discord.Interaction['LatteMaid'],
        error: app_commands.AppCommandError,
        /,
    ) -> None:
        await super().on_error(interaction, error)

    async def fake_translator(self, *, guild: Optional[discord.abc.Snowflake] = None) -> None:
        if self.translator is None:
            return
        commands = self._get_all_commands(guild=guild)
        for command in commands:
            await command.get_translated_payload(self.translator)
