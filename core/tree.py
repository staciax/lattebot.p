from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands

if TYPE_CHECKING:
    from .bot import LatteMiad


_log = logging.getLogger(__name__)


class LatteMaidTree(app_commands.CommandTree['LatteMaid']):
    async def interaction_check(self, interaction: discord.Interaction[LatteMiad], /) -> bool:
        user = interaction.user
        guild = interaction.guild
        locale = interaction.locale
        command = interaction.command

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
            if _ := await self.client.db.fetch_user(user.id):
                self.client.loop.create_task(self.client.db.remove_user(user.id))

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
        if interaction.user and isinstance(command, (app_commands.ContextMenu, app_commands.Command)):
            user_db = await self.client.db.fetch_user(interaction.user.id)
            if user_db is None:
                await self.client.db.add_user(interaction.user.id)
                # settings = await self.client.db.add_user_settings(interaction.user.id)
                # self.client.loop.create_task(self.client.db.create_user(user_id, locale=interaction.locale.value))
            elif user_db.locale is None:
                ...
                # await database.update_user_settings(interaction.user.id, locale=locale)
                # self.client.loop.create_task(self.client.db.update_user(interaction.user.id))

        return True

    async def sync(self, *, guild: discord.abc.Snowflake | None = None) -> list[app_commands.AppCommand]:
        synced = await super().sync(guild=guild)
        if synced:
            _log.info('synced %s application commands %s' % (len(synced), f'for guild {guild.id}' if guild else ''))
        return synced

    async def on_error(
        self,
        interaction: discord.Interaction['LatteMiad'],
        error: app_commands.AppCommandError,
        /,
    ) -> None:
        await super().on_error(interaction, error)

    async def insert_model_to_commands(self) -> None:
        server_app_commands = await self.fetch_commands()
        for server in server_app_commands:
            command = self.get_command(server.name, type=server.type)
            if command is None:
                _log.warning('not found command %s (type: %s)', server.name, server.type)
                continue
            command.extras['model'] = server

    async def fake_translator(self, *, guild: discord.abc.Snowflake | None = None) -> None:
        if self.translator is None:
            return
        commands = self._get_all_commands(guild=guild)
        for command in commands:
            await command.get_translated_payload(self.translator)

    # wait for discord adding this feature
    # fetch_commands with localizations

    async def fetch_commands(self, *, guild: discord.abc.Snowflake | None = None) -> list[app_commands.AppCommand]:
        if self.client.application_id is None:
            raise app_commands.errors.MissingApplicationID

        application_id = self.client.application_id

        from discord.http import Route

        if guild is None:
            commands = await self._http.request(
                Route('GET', '/applications/{application_id}/commands', application_id=application_id),
                params={'with_localizations': 1},
            )
        else:
            commands = await self._http.request(
                Route(
                    'GET',
                    '/applications/{application_id}/guilds/{guild_id}/commands',
                    application_id=application_id,
                    guild_id=guild.id,
                ),
                params={'with_localizations': 1},
            )

        return [app_commands.AppCommand(data=data, state=self._state) for data in commands]
