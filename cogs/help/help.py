from __future__ import annotations

from typing import TYPE_CHECKING, List, Union

import discord
from discord import app_commands, ui
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import bot_has_permissions, dynamic_cooldown
from discord.app_commands.commands import Command, Group
from discord.app_commands.models import AppCommand, AppCommandGroup, Argument
from discord.ext import commands

from core.checks import cooldown_short
from core.i18n import I18n, cog_i18n
from core.ui.embed import MiadEmbed as Embed
from core.ui.views import ViewAuthor
from core.utils.pages import LattePages, ListPageSource

if TYPE_CHECKING:
    from core.bot import LatteMaid

_ = I18n('help', __file__)


class HelpPageSource(ListPageSource):
    def __init__(
        self,
        cog: commands.Cog,
        source: List[Union[AppCommand, AppCommandGroup]],
    ) -> None:
        self.cog = cog
        super().__init__(
            sorted(source, key=lambda c: c.qualified_name if isinstance(c, AppCommandGroup) else c.name),
            per_page=6,
        )

    @staticmethod
    def default(cog: commands.Cog) -> Embed:
        emoji = getattr(cog, 'display_emoji', '')
        embed = Embed(
            title=f'{emoji} {cog.qualified_name}',
            description=cog.description + '\n' or _('No description provided') + '\n',
        )
        return embed

    def format_page(
        self,
        menu: HelpCommand,
        entries: List[Union[AppCommand, AppCommandGroup]],
    ) -> Embed:
        embed = self.default(self.cog)
        for command in entries:
            assert embed.description is not None
            embed.description += f'\n{command.mention} - {command.description}'

        return embed


class CogButton(ui.Button['HelpCommand']):
    def __init__(self, cog: commands.Cog, *args, **kwargs) -> None:
        self.cog = cog
        emoji = getattr(cog, 'display_emoji')
        super().__init__(emoji=emoji, style=discord.ButtonStyle.primary, *args, **kwargs)
        if self.emoji is None:
            self.label = cog.qualified_name

    def get_cog_app_commands(
        self,
        cog_app_commands: List[Union[Command, Group]],
    ) -> List[Union[AppCommand, AppCommandGroup]]:
        assert self.view is not None
        app_command_list = []
        for cog_app in cog_app_commands:
            for app_cmd in self.view.bot.get_app_commands():
                if isinstance(app_cmd, AppCommand):
                    if cog_app.qualified_name.lower() == app_cmd.name.lower():
                        if [option for option in app_cmd.options if isinstance(option, Argument)] or (
                            not len(app_cmd.options)
                        ):
                            app_command_list.append(app_cmd)

                        for option in app_cmd.options:
                            if isinstance(option, AppCommandGroup):
                                app_command_list.append(option)

        return app_command_list

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        self.view.source = HelpPageSource(self.cog, self.get_cog_app_commands(list(self.cog.walk_app_commands())))
        max_pages = self.view.source.get_max_pages()
        if max_pages is not None and max_pages > 1:
            self.view.add_nav_buttons()
        else:
            self.view.remove_nav_buttons()
        self.view.home_button.disabled = False
        await self.view.show_page(interaction, 0)


class HelpCommand(ViewAuthor, LattePages):
    def __init__(self, interaction: discord.Interaction[LatteMaid], cogs: List[str]) -> None:
        super().__init__(interaction, timeout=600.0)
        self.cogs = cogs
        self.embed: Embed = self.front_help_command_embed()
        self.home_button.emoji = self.bot.emoji.latte_icon
        self.go_to_last_page.row = 1
        self.go_to_first_page.row = 1
        self.go_to_previous_page.row = 1
        self.go_to_next_page.row = 1
        self.clear_items()

    def front_help_command_embed(self) -> Embed:
        assert self.bot.user is not None
        embed = Embed().secondary()
        embed.set_author(
            name=f'{self.bot.user.global_name} - Help',
            icon_url=self.bot.user.display_avatar,
        )
        # embed.set_image(url=str(self.bot.cdn.help_banner))
        return embed

    @ui.button(emoji='🏘️', style=discord.ButtonStyle.primary, disabled=True)
    async def home_button(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
        await interaction.response.defer()
        self.home_button.disabled = True
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
        for cog in sorted(self.bot.cogs.values(), key=lambda c: c.qualified_name):
            if cog.qualified_name not in self.cogs or len(list(cog.walk_app_commands())) <= 0:
                continue
            self.add_item(CogButton(cog=cog))

    async def callback(self) -> None:
        self.add_item(self.home_button)
        self.add_cog_buttons()
        await self.interaction.response.send_message(embed=self.embed, view=self)
        self.message = await self.interaction.original_response()


@cog_i18n(_)
class Help(commands.Cog, name='help'):
    """Help command"""

    def __init__(self, bot: LatteMaid):
        self.bot: LatteMaid = bot

    @app_commands.command(name=_T('help'), description=_T('help command'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @dynamic_cooldown(cooldown_short)
    async def help_command(self, interaction: discord.Interaction[LatteMaid]):
        cogs = ['About', 'Valorant']
        help_command = HelpCommand(interaction, cogs)
        await help_command.callback()


async def setup(bot: LatteMaid) -> None:
    await bot.add_cog(Help(bot))
