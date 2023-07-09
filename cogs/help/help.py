from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands, ui
from discord.app_commands import locale_str as _T
from discord.app_commands.commands import Command, Group
from discord.app_commands.models import AppCommand
from discord.ext import commands

from core.checks import bot_has_permissions, cooldown_short, dynamic_cooldown, user as user_check
from core.cog import Cog
from core.i18n import I18n, cog_i18n
from core.ui.embed import MiadEmbed as Embed
from core.ui.views import ViewAuthor
from core.utils.pages import LattePages, ListPageSource

if TYPE_CHECKING:
    from core.bot import LatteMaid

_ = I18n('help', __file__)


class HelpPageSource(ListPageSource):
    def __init__(self, cog: commands.Cog, source: list[Command[Any, ..., Any] | Group]) -> None:
        self.cog = cog
        entries = []
        for app in sorted(source, key=lambda c: c.qualified_name):
            if app.parent and app.parent._guild_ids:
                continue
            if app._guild_ids:
                continue
            entries.append(app)

        super().__init__(entries, per_page=6)

    @staticmethod
    def default(cog: commands.Cog, locale: discord.Locale) -> Embed:
        emoji = getattr(cog, 'display_emoji', '')

        description = cog.description
        if i18n := getattr(cog, '__i18n__', None):
            description = i18n.get_text('cog.description', locale, description)

        embed = Embed(
            title=f'{emoji} {cog.qualified_name}',
            description=description + '\n',
        )
        return embed

    def format_page(
        self,
        menu: HelpCommand,
        entries: list[Command[Any, ..., Any] | Group],
    ) -> Embed:
        embed = self.default(self.cog, menu.locale)
        for command in entries:
            assert embed.description is not None
            name = command.qualified_name
            description = command.description

            model: AppCommand | None = command.extras.get('model', None)
            if model is not None:
                assert isinstance(model, AppCommand)
                name = model.mention
                description = model.description_localizations.get(menu.locale, command.description)

            embed.description += f'\n{name} - {description}'

        return embed


class CogButton(ui.Button['HelpCommand']):
    def __init__(self, cog: commands.Cog, *args, **kwargs) -> None:
        self.cog = cog
        emoji = getattr(cog, 'display_emoji')
        super().__init__(emoji=emoji, style=discord.ButtonStyle.primary, *args, **kwargs)
        if self.emoji is None:
            self.label = cog.qualified_name

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None

        self.view.source = HelpPageSource(self.cog, list(self.cog.walk_app_commands()))

        max_pages = self.view.source.get_max_pages()
        if max_pages is not None and max_pages > 1:
            self.view.add_nav_buttons()
        else:
            self.view.remove_nav_buttons()

        self.disabled = True
        for child in self.view.children:
            if isinstance(child, CogButton) and child != self:
                child.disabled = False
        self.view.home_button.disabled = False
        await self.view.show_page(interaction, 0)


class HelpCommand(ViewAuthor, LattePages):
    def __init__(self, interaction: discord.Interaction[LatteMaid], cogs: list[str]) -> None:
        super().__init__(interaction, timeout=600.0)
        self.cogs = cogs
        self.embed: Embed = self.front_help_command_embed(interaction)
        self.home_button.emoji = self.bot.emoji.latte_icon
        self.go_to_last_page.row = 1
        self.go_to_first_page.row = 1
        self.go_to_previous_page.row = 1
        self.go_to_next_page.row = 1
        self.cooldown = commands.CooldownMapping.from_cooldown(5.0, 15.0, user_check)
        self.clear_items()

    def _update_labels(self, page_number: int) -> None:
        super()._update_labels(page_number)
        self.go_to_next_page.label = 'next'
        self.go_to_previous_page.label = 'prev'

    def front_help_command_embed(self, interaction: discord.Interaction[LatteMaid]) -> Embed:
        assert self.bot.user is not None
        embed = Embed(timestamp=interaction.created_at).white()
        embed.set_author(
            name=f'{self.bot.user.display_name} - ' + _('help.command', interaction.locale),
            icon_url=self.bot.user.display_avatar,
        )
        embed.set_image(url='https://cdn.discordapp.com/attachments/1001848697316987009/1001848873385472070/help_banner.png')
        return embed

    @ui.button(emoji='🏘️', style=discord.ButtonStyle.primary, disabled=True)
    async def home_button(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
        await interaction.response.defer()
        self.home_button.disabled = True
        for child in self.children:
            if isinstance(child, CogButton):
                child.disabled = False
        self.remove_nav_buttons()
        if self.message is not None:
            await self.message.edit(embed=self.embed, view=self)

    def add_nav_buttons(self) -> None:
        self.add_item(self.go_to_first_page)
        self.add_item(self.go_to_previous_page)
        self.add_item(self.go_to_next_page)
        self.add_item(self.go_to_last_page)

    def remove_nav_buttons(self) -> None:
        self.remove_item(self.go_to_first_page)
        self.remove_item(self.go_to_previous_page)
        self.remove_item(self.go_to_next_page)
        self.remove_item(self.go_to_last_page)

    def add_cog_buttons(self) -> None:
        for cog in sorted(self.bot.cogs.values(), key=lambda c: c.qualified_name.lower()):
            if cog.qualified_name.lower() not in self.cogs:
                continue
            if not len(list(cog.walk_app_commands())):
                continue
            self.add_item(CogButton(cog=cog))

    async def callback(self) -> None:
        self.add_item(self.home_button)
        self.add_cog_buttons()
        await self.interaction.response.send_message(embed=self.embed, view=self)
        self.message = await self.interaction.original_response()


@cog_i18n(_)
class Help(Cog, name='help'):
    """Help command"""

    def __init__(self, bot: LatteMaid):
        self.bot: LatteMaid = bot

    @app_commands.command(name=_T('help'), description=_T('help command'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @dynamic_cooldown(cooldown_short)
    async def help_command(self, interaction: discord.Interaction[LatteMaid]):
        cogs = ['about', 'valorant']
        help_command = HelpCommand(interaction, cogs)
        await help_command.callback()


async def setup(bot: LatteMaid) -> None:
    await bot.add_cog(Help(bot))
