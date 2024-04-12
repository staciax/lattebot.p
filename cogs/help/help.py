from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands, ui
from discord.app_commands import locale_str as _T
from discord.app_commands.commands import Command, ContextMenu, Group
from discord.app_commands.models import AppCommand
from discord.ext import commands

from core.checks import bot_has_permissions, cooldown_short, dynamic_cooldown, user as user_check
from core.cog import MaidCog
from core.i18n import I18n, cog_i18n
from core.ui.embed import MiadEmbed as Embed
from core.ui.views import ViewAuthor
from core.utils.pages import LattePages, ListPageSource

if TYPE_CHECKING:
    from core.bot import LatteMaid

_ = I18n('help', __file__)


def help_command_embed(interaction: discord.Interaction[LatteMaid]) -> Embed:
    bot = interaction.client
    embed = Embed(timestamp=interaction.created_at).white()
    embed.set_author(
        name=f'{bot.user.display_name} - ' + _('help.command', interaction.locale),
        icon_url=bot.user.display_avatar,
    )
    embed.set_image(
        url='https://cdn.discordapp.com/attachments/1001848697316987009/1001848873385472070/help_banner.png'
    )
    return embed


def cog_embed(cog: commands.Cog | MaidCog, locale: discord.Locale) -> Embed:
    emoji = getattr(cog, 'display_emoji', '')

    description = cog.description
    if i18n := getattr(cog, '__i18n__', None):
        description = i18n.get_text('cog.description', locale, description)

    embed = Embed(
        title=f'{emoji} {cog.qualified_name}',
        description=description + '\n',
    )
    return embed


class HelpPageSource(ListPageSource):
    def __init__(self, cog: commands.Cog | MaidCog, source: list[Command[Any, ..., Any] | Group]) -> None:
        super().__init__(sorted(source, key=lambda c: c.qualified_name), per_page=6)
        self.cog = cog

    def format_page(
        self,
        menu: HelpCommandView,
        entries: list[Command[Any, ..., Any] | Group],
    ) -> Embed:
        embed = cog_embed(self.cog, menu.locale)
        assert embed.description is not None
        for command in entries:
            name = command.qualified_name
            description = command.description

            model: AppCommand | None = command.extras.get('model', None)
            if model is not None:
                assert isinstance(model, AppCommand)
                name = model.mention
                description = model.description_localizations.get(menu.locale, description)

            embed.description += f'\n{name} - {description}'

        return embed


class CogButton(ui.Button['HelpCommandView']):
    def __init__(
        self,
        cog: commands.Cog | MaidCog,
        entries: list[Command[Any, ..., Any] | Group],
        **kwargs: Any,
    ) -> None:
        super().__init__(emoji=getattr(cog, 'display_emoji'), style=discord.ButtonStyle.primary, **kwargs)  # noqa: B009
        self.cog = cog
        self.entries = entries
        if self.emoji is None:
            self.label = cog.qualified_name

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        self.view.source = HelpPageSource(self.cog, self.entries)

        max_pages = self.view.source.get_max_pages()
        if max_pages > 1:
            self.view._add_nav_buttons()
        else:
            self.view._remove_nav_buttons()

        self.disabled = True
        for child in self.view.children:
            if isinstance(child, CogButton) and child != self:
                child.disabled = False

        self.view.home_button.disabled = False
        await self.view.show_page(interaction, 0)


class HelpCommandView(ViewAuthor, LattePages):
    def __init__(self, interaction: discord.Interaction[LatteMaid], allowed_cogs: tuple[str, ...]):
        super().__init__(interaction=interaction, timeout=60.0 * 30)  # 30 minutes
        self.allowed_cogs = allowed_cogs
        self.embed: Embed = help_command_embed(interaction)
        self.cooldown = commands.CooldownMapping.from_cooldown(8.0, 15.0, user_check)  # overide default cooldown
        self.go_to_last_page.row = self.go_to_first_page.row = self.go_to_previous_page.row = (
            self.go_to_next_page.row
        ) = 1
        self.clear_items()
        self.add_item(self.home_button)

    def _update_labels(self, page_number: int) -> None:
        super()._update_labels(page_number)
        self.go_to_next_page.label = 'next'
        self.go_to_previous_page.label = 'prev'
        # TODO: i18n in lattepages class

    def _add_nav_buttons(self) -> None:
        self.add_item(self.go_to_first_page)
        self.add_item(self.go_to_previous_page)
        self.add_item(self.go_to_next_page)
        self.add_item(self.go_to_last_page)

    def _remove_nav_buttons(self) -> None:
        self.remove_item(self.go_to_first_page)
        self.remove_item(self.go_to_previous_page)
        self.remove_item(self.go_to_next_page)
        self.remove_item(self.go_to_last_page)

    async def _build_cog_buttons(self) -> None:
        user = self.interaction.user
        channel = self.interaction.channel

        async def command_available(command: Command[Any, ..., Any] | Group | ContextMenu) -> bool:
            # it fine my bot is not nsfw
            # if (
            #     command.nsfw
            #     and channel is not None
            #     and not isinstance(channel, (discord.GroupChannel, discord.DMChannel))
            #     and not channel.is_nsfw()
            # ):
            #     return False

            if isinstance(command, Group):
                return False

            if await self.bot.is_owner(user):
                return True

            if command._guild_ids:
                return False

            # ignore slash commands that are not global
            if not isinstance(command, ContextMenu) and command.parent and command.parent._guild_ids:
                return False

            # ignore slash commands you can't run
            if command.checks and not await discord.utils.async_all(f(self.interaction) for f in command.checks):
                return False

            # ignore slash commands you not have default permissions
            if (
                command.default_permissions
                and channel is not None
                and isinstance(user, discord.Member)
                and not channel.permissions_for(user) >= command.default_permissions
            ):
                return False

            return True

        for cog in sorted(self.bot.cogs.values(), key=lambda c: c.qualified_name.lower()):
            if cog.qualified_name.lower() not in self.allowed_cogs:
                continue

            if not list(cog.walk_app_commands()):
                continue

            entries = []
            for command in cog.walk_app_commands():
                if not await command_available(command):
                    continue
                entries.append(command)

            # TODO: implement context menu
            # if isinstance(cog, Cog):
            #     context_menus = cog.get_context_menus()
            #     for menu in context_menus:
            #         if not await command_available(menu):
            #             continue
            #         entries.append(menu)

            if not entries:
                continue

            self.add_item(CogButton(cog, entries))

    async def before_callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        if self.locale == interaction.locale:
            return
        self.locale = interaction.locale
        self.embed = help_command_embed(interaction)

    async def start(self) -> None:
        await self._build_cog_buttons()
        await self.interaction.response.send_message(embed=self.embed, view=self)
        self.message = await self.interaction.original_response()

    @ui.button(emoji='🏘️', style=discord.ButtonStyle.primary, disabled=True)
    async def home_button(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
        # disable home button
        button.disabled = True

        # disable all cog buttons
        for child in self.children:
            if isinstance(child, CogButton):
                child.disabled = False

        # remove nav buttons
        self._remove_nav_buttons()

        await interaction.response.edit_message(embed=self.embed, view=self)


@cog_i18n(_)
class Help(MaidCog, name='help'):
    """Help command"""

    def __init__(self, bot: LatteMaid):
        self.bot: LatteMaid = bot

    @app_commands.command(name=_T('help'), description=_T('help command'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @dynamic_cooldown(cooldown_short)
    async def help_command(self, interaction: discord.Interaction[LatteMaid]):
        cogs = ('about', 'valorant')
        help_command = HelpCommandView(interaction, cogs)
        await help_command.start()
