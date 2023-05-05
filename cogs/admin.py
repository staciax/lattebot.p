from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, Optional

import discord
from discord import Interaction, app_commands
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import bot_has_permissions
from discord.ext import commands

from core.checks import owner_only
from core.errors import CommandError
from core.utils.chat_formatting import bold, inline
from core.utils.useful import MiadEmbed

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__file__)

# fmt: off
EXTENSIONS = Literal[
    'cogs.developer',
    'cogs.events',
    'cogs.help',
    'cogs.about',
    'cogs.valorant',
    'cogs.role_connection',
]
# fmt: on


class Developer(commands.Cog, name='developer'):
    """Developer commands"""

    def __init__(self, bot: LatteMaid) -> None:
        self.bot = bot

    extension = app_commands.Group(
        name=_T('_ext'),
        description=_T('extension manager'),
        default_permissions=discord.Permissions(
            administrator=True,
        ),
    )

    @extension.command(name=_T('load'), description=_T('Load an extension'))
    @app_commands.describe(extension=_T('extension name'))
    @app_commands.rename(extension=_T('extension'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def extension_load(self, interaction: Interaction[LatteMaid], extension: Literal[EXTENSIONS]) -> None:
        try:
            await self.bot.load_extension(f'{extension}')
            _log.info(f'Loading extension {extension}')
        except commands.ExtensionAlreadyLoaded:
            raise CommandError(f"The extension is already loaded.")
        except Exception as e:
            _log.error(e)
            raise CommandError('The extension load failed')
        else:
            embed = MiadEmbed(description=f"Load : `{extension}`").success()
            await interaction.response.send_message(embed=embed, ephemeral=True, silent=True)

    @extension.command(name=_T('unload'), description=_T('Unload an extension'))
    @app_commands.describe(extension=_T('extension name'))
    @app_commands.rename(extension=_T('extension'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def extension_unload(self, interaction: Interaction[LatteMaid], extension: EXTENSIONS) -> None:
        try:
            await self.bot.unload_extension(f'{extension}')
            _log.info(f'Unloading extension {extension}')
        except commands.ExtensionNotLoaded:
            raise CommandError(f'The extension was not loaded.')
        except Exception as e:
            _log.error(e)
            raise CommandError('The extension unload failed')
        else:
            embed = MiadEmbed(description=f"Unload : `{extension}`").success()
            await interaction.response.send_message(embed=embed, ephemeral=True, silent=True)

    @extension.command(name=_T('reload'))
    @app_commands.describe(extension=_T('extension name'))
    @app_commands.rename(extension=_T('extension'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def extension_reload(self, interaction: Interaction[LatteMaid], extension: EXTENSIONS) -> None:
        """Reloads an extension."""

        try:
            await self.bot.reload_extension(f'{extension}')
            _log.info(f'Reloading extension {extension}')
        except commands.ExtensionNotLoaded:
            raise CommandError(f'The extension was not loaded.')
        except commands.ExtensionNotFound:
            raise CommandError(f'The Extension Not Found')
        except Exception as e:
            _log.error(e)
            raise CommandError('The extension reload failed')
        else:
            embed = MiadEmbed(description=f"Reload : `{extension}`").success()
            await interaction.response.send_message(embed=embed, ephemeral=True, silent=True)

    @app_commands.command(name='_sync_tree')
    @app_commands.rename(guild_id=_T('guild_id'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def sync_tree(self, interaction: Interaction[LatteMaid], guild_id: Optional[int] = None) -> None:
        await interaction.response.defer(ephemeral=True)

        if guild_id is not None:
            obj = discord.Object(id=guild_id)
            await self.bot.tree.sync(guild=obj)
            return
        await self.bot.tree.sync()

        embed = MiadEmbed(description=f"Sync Tree").success()
        if guild_id is not None:
            embed.description = f"Sync Tree : `{guild_id}`"

        # refresh application commands
        await self.bot.fetch_app_commands()

        await interaction.followup.send(embed=embed, ephemeral=True, silent=True)

    # @load.autocomplete('extension')
    # @unload.autocomplete('extension')
    # @reload_.autocomplete('extension')
    # async def tags_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
    #     """Autocomplete for extension names."""
    #
    #     if interaction.user.id != self.bot.owner_id:
    #         return [
    #             app_commands.Choice(name='Only owner can use this command', value='Owner only can use this command')]
    #
    #     cogs = [extension.lower() for extension in self.bot._initial_extensions if extension.lower() != 'cogs.admin']
    #     return [app_commands.Choice(name=cog, value=cog) for cog in cogs]

    blacklist = app_commands.Group(
        name=_T('_blacklist'),
        description=_T('Blacklist commands'),
        default_permissions=discord.Permissions(
            administrator=True,
        ),
    )

    @blacklist.command(name='add', description=_T('Add user or guild to blacklist'))
    @app_commands.describe(object_id=_T('Object ID'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def blacklist_add(self, interaction: Interaction[LatteMaid], object_id: str) -> None:
        await interaction.response.defer(ephemeral=True)

        if object_id in self.bot.db._blacklist:  # TODO: fix this
            raise CommandError(f'`{object_id}` is already in blacklist')

        await self.bot.db.create_blacklist(id=int(object_id))

        blacklist = (
            await self.bot.fetch_user(int(object_id))
            or self.bot.get_guild(int(object_id))
            or await self.bot.fetch_guild(int(object_id))
            or object_id
        )
        if isinstance(blacklist, (discord.User, discord.Guild)):
            blacklist = f"{blacklist} {inline(f'({blacklist.id})')}"

        embed = MiadEmbed(
            description=f"{blacklist} are now blacklisted.",
        ).success()

        await interaction.followup.send(embed=embed, silent=True)

    @blacklist.command(name=_T('remove'), description=_T('Remove a user or guild from the blacklist'))
    @app_commands.describe(object_id=_T('Object ID'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def blacklist_remove(self, interaction: Interaction[LatteMaid], object_id: str):
        await interaction.response.defer(ephemeral=True)

        if object_id not in self.bot.db._blacklist:
            raise CommandError(f'`{object_id}` is not in blacklist')

        await self.bot.db.delete_blacklist(int(object_id))

        blacklist = (
            await self.bot.fetch_user(int(object_id))
            or self.bot.get_guild(int(object_id))
            or await self.bot.fetch_guild(int(object_id))
            or object_id
        )

        if isinstance(blacklist, (discord.User, discord.Guild)):
            blacklist = f"{blacklist} {inline(f'({blacklist.id})')}"

        embed = MiadEmbed(description=f"{blacklist} are now unblacklisted.").success()

        await interaction.followup.send(embed=embed, silent=True)

    @blacklist.command(name=_T('check'), description=_T('Check if a user or guild is blacklisted'))
    @app_commands.describe(object_id=_T('Object ID'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def blacklist_check(self, interaction: Interaction[LatteMaid], object_id: str):
        await interaction.response.defer(ephemeral=True)

        embed = MiadEmbed(description=f'{bold(object_id)} is blacklisted.').error()

        if object_id not in self.bot.db.blacklist:
            embed.description = f"{bold(object_id)} is not blacklisted."
            embed.success()

        await interaction.followup.send(embed=embed, silent=True)

    # @blacklist.command(name=_T('list'), description=_T('Lists all blacklisted users'))
    # @owner_only()
    # async def blacklist_list(self, interaction: Interaction[LatteMaid]):
    #     await interaction.response.defer(ephemeral=True)


async def setup(bot: LatteMaid) -> None:
    if bot.support_guild_id is not None:
        await bot.add_cog(Developer(bot), guilds=[discord.Object(id=bot.support_guild_id)])
    else:
        _log.warning('Support guild id is not set. Developer cog will not be loaded.')
