from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

import discord
from discord import app_commands

if TYPE_CHECKING:
    from .bot import LatteMaid

_log = logging.getLogger(__name__)

# TODO: improve this


class LatteMaidTree(app_commands.CommandTree['LatteMaid']):
    async def interaction_check(self, interaction: discord.Interaction[LatteMaid], /) -> bool:
        if await self.client.is_owner(interaction.user):
            return True

        user_id = interaction.user.id
        guild = interaction.guild

        # TODO: spam check

        if user_id in self.client.db._blacklist:
            _log.info('blacklisted user tried to use bot %s', user_id)

            await interaction.response.send_message(
                'You are blacklisted from using this bot.',
                ephemeral=True,
            )

            # remove user from database
            if user := await self.client.db.get_user(user_id):
                self.client.loop.create_task(self.client.db.delete_user(user.id))

            return False

        if guild is not None and guild.id in self.client.db._blacklist:
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
        if isinstance(interaction.command, app_commands.Command):  # TODO: context menu support
            user_db = await self.client.db.get_user(user_id)
            if user_db is None:
                self.client.loop.create_task(self.client.db.create_user(user_id, locale=interaction.locale.value))
            elif user_db.locale != interaction.locale.value:
                self.client.loop.create_task(self.client.db.update_user(user_id, locale=interaction.locale.value))

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
        self.client.dispatch('app_command_error', interaction, error)

    async def fake_translator(self, *, guild: Optional[discord.abc.Snowflake] = None) -> None:
        commands = self._get_all_commands(guild=guild)
        assert self.translator is not None
        for command in commands:
            await command.get_translated_payload(self.translator)
