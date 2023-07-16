from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import discord
from discord import Interaction, app_commands
from discord.app_commands import locale_str as _T
from discord.ext import commands

from core.bot import LatteMaid
from core.checks import bot_has_permissions, owner_only
from core.database.models.blacklist import BlackList
from core.errors import AppCommandError
from core.ui.embed import MiadEmbed as Embed
from core.utils.chat_formatting import inline
from core.utils.pages import LattePages, ListPageSource

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__name__)

EXTENSIONS = Literal[
    'cogs.about',
    'cogs.errors',
    'cogs.events',
    'cogs.help',
    'cogs.jsk',
    'cogs.stats',
    'cogs.valorant',
    'cogs.test',
]


class BlackListPageSource(ListPageSource):
    def __init__(self, entries: list[BlackList], per_page: int = 12):
        super().__init__(entries, per_page)

    async def format_page(self, menu: BlackListPages, entries: list[BlackList]) -> Embed:
        pages = []
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
            pages.append(f'{index + 1}. {entry.id}')

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            menu.embed.set_footer(text=footer)

        menu.embed.description = '\n'.join(pages)
        return menu.embed


class BlackListPages(LattePages):
    def __init__(self, source: BlackListPageSource, *, interaction: Interaction[LatteMaid]):
        super().__init__(source, interaction=interaction)
        self.embed: Embed = Embed(title='Blacklist').dark()


class Developer(commands.Cog, name='developer'):
    """Developer commands"""

    def __init__(self, bot: LatteMaid) -> None:
        self.bot = bot

    extension = app_commands.Group(
        name=_T('ext'),
        description=_T('extension manager'),
        default_permissions=discord.Permissions(
            administrator=True,
        ),
        guild_only=True,
    )

    @extension.command(name=_T('load'), description=_T('Load an extension'))
    @app_commands.describe(extension=_T('extension name'))
    @app_commands.rename(extension=_T('extension'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def extension_load(self, interaction: Interaction[LatteMaid], extension: Literal[EXTENSIONS]) -> None:
        await self.bot.load_extension(f'{extension}')

        embed = Embed(description=f"**Loaded**: `{extension}`").success()
        await interaction.response.send_message(embed=embed, ephemeral=True, silent=True)

    @extension.command(name=_T('unload'), description=_T('Unload an extension'))
    @app_commands.describe(extension=_T('extension name'))
    @app_commands.rename(extension=_T('extension'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def extension_unload(self, interaction: Interaction[LatteMaid], extension: EXTENSIONS) -> None:
        await self.bot.unload_extension(f'{extension}')

        embed = Embed(description=f'**Unloaded**: `{extension}`').success()
        await interaction.response.send_message(embed=embed, ephemeral=True, silent=True)

    @extension.command(name=_T('reload'))
    @app_commands.describe(extension=_T('extension name'))
    @app_commands.rename(extension=_T('extension'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def extension_reload(self, interaction: Interaction[LatteMaid], extension: EXTENSIONS) -> None:
        """Reloads an extension."""

        await self.bot.reload_extension(f'{extension}')

        embed = Embed(description=f"**Reloaded**: `{extension}`").success()
        await interaction.response.send_message(embed=embed, ephemeral=True, silent=True)

    @app_commands.command(name='sync', description='Syncs the application commands to Discord.')
    @app_commands.rename(guild_id=_T('guild_id'))
    @app_commands.describe(guild_id=_T('target guild id'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @owner_only()
    async def sync_tree(self, interaction: Interaction[LatteMaid], guild_id: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)

        if guild_id is not None and guild_id.isdigit():
            obj = discord.Object(id=int(guild_id))
            await self.bot.tree.sync(guild=obj)
            return
        synced = await self.bot.tree.sync()

        embed = Embed(description=f'sync tree: {len(synced)}').success()
        if guild_id is not None:
            assert embed.description is not None
            embed.description += f' : `{guild_id}`'

        # refresh application commands model
        await self.bot.tree.insert_model_to_commands()

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
        guild_only=True,
    )

    @blacklist.command(name='add', description=_T('Add user or guild to blacklist'))
    @app_commands.describe(object_id=_T('Object ID'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def blacklist_add(self, interaction: Interaction[LatteMaid], object_id: str) -> None:
        # NOTE: int maximum length is 18 but currently discord object id more than 18

        if not object_id.isdigit():
            raise AppCommandError(f'`{object_id}` is not a valid ID')

        await interaction.response.defer(ephemeral=True)

        if self.bot.is_blocked(int(object_id)):
            raise AppCommandError(f'`{object_id}` is already in blacklist')

        await self.bot.db.add_blacklist(int(object_id))

        blacklist = (
            self.bot.get_user(int(object_id))
            or self.bot.get_guild(int(object_id))
            or await self.bot.fetch_user(int(object_id))
            or await self.bot.fetch_guild(int(object_id))
            or object_id
        )
        if isinstance(blacklist, (discord.User, discord.Guild)):
            blacklist = f"{blacklist} {inline(f'({blacklist.id})')}"

        embed = Embed(
            description=f'{blacklist} are now blacklisted.',
        ).success()

        await interaction.followup.send(embed=embed, silent=True)

    @blacklist.command(name=_T('remove'), description=_T('Remove a user or guild from the blacklist'))
    @app_commands.describe(object_id=_T('Object ID'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def blacklist_remove(self, interaction: Interaction[LatteMaid], object_id: str):
        if not object_id.isdigit():
            raise AppCommandError(f'`{object_id}` is not a valid ID')

        await interaction.response.defer(ephemeral=True)

        if int(object_id) not in self.bot.db._blacklist:
            raise AppCommandError(f'`{object_id}` is not in blacklist')

        await self.bot.db.remove_blacklist(int(object_id))

        blacklist = (
            self.bot.get_user(int(object_id))
            or await self.bot.fetch_user(int(object_id))
            or self.bot.get_guild(int(object_id))
            or await self.bot.fetch_guild(int(object_id))
            or object_id
        )

        if isinstance(blacklist, (discord.User, discord.Guild)):
            blacklist = f'{blacklist} {inline(f"({blacklist.id})")}'

        embed = Embed(description=f'{blacklist} are now unblacklisted.').success()

        await interaction.followup.send(embed=embed, silent=True)

    # @blacklist.command(name=_T('check'), description=_T('Check if a user or guild is blacklisted'))
    # @app_commands.describe(object_id=_T('Object ID'))
    # @bot_has_permissions(send_messages=True, embed_links=True)
    # @owner_only()
    # async def blacklist_check(self, interaction: Interaction[LatteMaid], object_id: str):
    #     if not object_id.isdigit():
    #         raise AppCommandError(f'`{object_id}` is not a valid ID')

    #     await interaction.response.defer(ephemeral=True)

    #     embed = Embed(description=f'{bold(object_id)} is blacklisted.').error()

    #     if int(object_id) not in self.bot.db._blacklist:
    #         embed.description = f'{bold(object_id)} is not blacklisted.'
    #         embed.success()

    #     await interaction.followup.send(embed=embed, silent=True)

    @blacklist.command(name=_T('list'), description=_T('Lists all blacklisted users'))
    @owner_only()
    async def blacklist_list(self, interaction: Interaction[LatteMaid]):
        await interaction.response.defer(ephemeral=True)

        blacklists = []
        async for blacklist in self.bot.db.get_blacklists():
            blacklists.append(blacklist)

        source = BlackListPageSource(blacklists)
        pages = BlackListPages(source, interaction=interaction)

        await pages.start()


async def setup(bot: LatteMaid) -> None:
    if bot.support_guild_id is not None:
        await bot.add_cog(Developer(bot), guilds=[discord.Object(id=bot.support_guild_id)])
    else:
        _log.warning('Support guild id is not set. Developer cog will not be loaded.')
