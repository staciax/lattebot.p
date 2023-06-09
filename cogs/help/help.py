from __future__ import annotations

from typing import TYPE_CHECKING, List, Union

import discord
from discord import Interaction, app_commands, ui
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import bot_has_permissions, dynamic_cooldown
from discord.ext import commands
from utils.pages import LattePages, ListPageSource
from utils.ui import LatteEmbed as Embed
from utils.views import ViewAuthor

from core.checks import cooldown_short
from core.i18n import _

if TYPE_CHECKING:
    from core.bot import LatteMaid


class HelpPageSource(ListPageSource):
    def __init__(self, source: List[app_commands.AppCommand]) -> None:
        super().__init__(source, per_page=6)

    @staticmethod
    def default(cog: commands.Cog) -> Embed:
        emoji = getattr(cog, 'display_emoji', '')
        embed = Embed(
            title=f"{emoji} {cog.qualified_name}",
            description=cog.description + '\n' or _('No description provided') + '\n',
        )
        return embed

    def format_page(self, menu: HelpCommand, entries: List[app_commands.AppCommand]) -> Embed:
        embed = self.default(menu.current_cog)

        for command in sorted(
            entries, key=lambda c: c.qualified_name if isinstance(c, app_commands.AppCommandGroup) else c.name
        ):
            command_des = command.description.lower().split(" | ")
            index = 1 if menu.interaction.locale != discord.Locale.thai and len(command_des) > 1 else 0

            if embed.description is not None:
                embed.description += f'\n{command.mention} - {command_des[index]}'

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
        cog_app_commands: List[Union[app_commands.Command, app_commands.Group]],
    ) -> List[app_commands.AppCommand]:
        assert self.view is not None
        fetch_app_commands = self.view.bot.get_app_commands()
        app_command_list = []
        for c_app in cog_app_commands:
            for f_app in fetch_app_commands:
                if f_app.type == discord.AppCommandType.chat_input:
                    if c_app.qualified_name.lower() == f_app.name.lower():
                        if [option for option in f_app.options if isinstance(option, app_commands.Argument)] or (
                            not len(f_app.options)
                        ):
                            app_command_list.append(f_app)
                        for option in f_app.options:
                            if isinstance(option, app_commands.AppCommandGroup):
                                app_command_list.append(option)

        return app_command_list

    async def callback(self, interaction: Interaction[LatteMaid]) -> None:
        assert self.view is not None

        self.view.current_cog = self.cog
        self.view.source = HelpPageSource(self.get_cog_app_commands(list(self.cog.walk_app_commands())))

        max_pages = self.view.get_max_pages()
        if max_pages is not None and max_pages > 1:
            self.view.add_nav_buttons()
        else:
            self.view.remove_nav_buttons()
        self.view.home_button.disabled = False
        await self.view.show_page(interaction, 0)


class HelpCommand(ViewAuthor, LattePages):
    def __init__(self, interaction: Interaction[LatteMaid], cogs: List[str]) -> None:
        super().__init__(interaction, timeout=600.0)
        self.cogs = cogs
        self.current_cog: commands.Cog = discord.utils.MISSING
        self.embed: Embed = self.front_help_command_embed()
        self.home_button.emoji = self.bot.emoji.latte_icon
        self.first_page.row = self.previous_page.row = self.next_page.row = self.last_page.row = 1
        self.clear_items()

    def front_help_command_embed(self) -> Embed:
        embed = Embed.secondary()
        embed.set_author(
            name=f'{self.bot.user.display_name} - Help',
            icon_url=self.bot.user.display_avatar,
        )
        embed.set_image(url=str(self.bot.cdn.help_banner))
        return embed

    @ui.button(emoji='🏘️', style=discord.ButtonStyle.primary, disabled=True)
    async def home_button(self, interaction: Interaction[LatteMaid], button: ui.Button) -> None:
        await interaction.response.defer()
        self.home_button.disabled = True
        self.remove_nav_buttons()
        if self.message is not None:
            await self.message.edit(embed=self.embed, view=self)

    def add_nav_buttons(self) -> None:
        self.add_item(self.first_page)
        self.add_item(self.previous_page)
        self.add_item(self.next_page)
        self.add_item(self.last_page)

    def remove_nav_buttons(self) -> None:
        self.remove_item(self.first_page)
        self.remove_item(self.previous_page)
        self.remove_item(self.next_page)
        self.remove_item(self.last_page)

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


class Help(commands.Cog, name='help'):
    """Help command"""

    def __init__(self, bot: LatteMaid):
        self.bot: LatteMaid = bot

    @app_commands.command(name=_T('help'), description=_T('help command'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @dynamic_cooldown(cooldown_short)
    async def help_command(self, interaction: Interaction[LatteMaid]):
        cogs = ['About', 'Valorant']
        help_command = HelpCommand(interaction, cogs)
        await help_command.callback()


async def setup(bot: LatteMaid) -> None:
    await bot.add_cog(Help(bot))
