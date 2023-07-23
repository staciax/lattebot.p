from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Iterable, TypeVar, Union

import discord
from discord import Interaction, app_commands
from discord.app_commands import ContextMenu, Group, locale_str
from discord.ext import commands
from discord.utils import MISSING

if TYPE_CHECKING:
    from typing_extensions import Self

    from .bot import LatteMiad


T = TypeVar('T')
Coro = Coroutine[Any, Any, T]
Binding = Union['Group', 'commands.Cog']
GroupT = TypeVar('GroupT', bound='Binding')

ContextMenuCallback = Union[
    Callable[[GroupT, 'Interaction[Any]', discord.Member], Coro[Any]],
    Callable[[GroupT, 'Interaction[Any]', discord.User], Coro[Any]],
    Callable[[GroupT, 'Interaction[Any]', discord.Message], Coro[Any]],
    Callable[[GroupT, 'Interaction[Any]', Union[discord.Member, discord.User]], Coro[Any]],
]

_log = logging.getLogger(__name__)


# https://github.com/InterStella0/stella_bot/blob/bf5f5632bcd88670df90be67b888c282c6e83d99/utils/cog.py#L28
def context_menu(
    *,
    name: str | locale_str = MISSING,
    nsfw: bool = False,
    guilds: list[discord.abc.Snowflake] = MISSING,
    auto_locale_strings: bool = True,
    extras: dict[Any, Any] = MISSING,
) -> Callable[[ContextMenuCallback], ContextMenu]:
    def inner(func: Any) -> Any:
        nonlocal name
        func.__context_menu_guilds__ = guilds
        if name is MISSING:
            name = func.__name__
        func.__context_menu__ = dict(
            name=name,
            nsfw=nsfw,
            auto_locale_strings=auto_locale_strings,
            extras=extras,
        )
        return func

    return inner


class Cog(commands.Cog):
    __cog_context_menus__: list[app_commands.ContextMenu]

    def _get_file_path(self) -> str | None:
        module = sys.modules[self.__module__]
        file_path = module.__file__
        return file_path

    def get_context_menus(self) -> list[app_commands.ContextMenu]:
        return [menu for menu in self.__cog_context_menus__ if isinstance(menu, app_commands.ContextMenu)]

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction[LatteMiad],
        error: app_commands.AppCommandError,
    ) -> None:
        if interaction.client.is_debug_mode():
            command = interaction.command
            if command is not None:
                _log.error('exception in %s command on %s cog', command.name, self.qualified_name, exc_info=error)
            else:
                _log.error('exception on %s cog', self.qualified_name, exc_info=error)
        interaction.client.dispatch('app_command_error', interaction, error)

    async def _inject(
        self,
        bot: LatteMiad,
        override: bool,
        guild: discord.abc.Snowflake | None,
        guilds: list[discord.abc.Snowflake],
    ) -> Self:
        await super()._inject(bot, override, guild, guilds)

        # context menus in cog
        for method_name in dir(self):
            method = getattr(self, method_name)
            if context_values := getattr(method, '__context_menu__', None):
                menu = app_commands.ContextMenu(callback=method, **context_values)
                menu.on_error = self.cog_app_command_error
                setattr(menu, '__binding__', self)
                context_values['context_menu_class'] = menu
                bot.tree.add_command(menu, guilds=method.__context_menu_guilds__)
                try:
                    self.__cog_context_menus__.append(menu)
                except AttributeError:
                    self.__cog_context_menus__ = [menu]

        # app commands localization
        translator = bot.translator
        fp = self._get_file_path()
        if fp is not None:
            await translator.load_from_files(self.qualified_name, fp)

            for app_command in self.get_app_commands():
                if app_command._guild_ids:
                    continue
                translator.add_app_command_localization(app_command)

            await translator.save_to_files(
                [c.qualified_name for c in self.get_app_commands() if not c._guild_ids],  # exclude guild commands
                self.qualified_name,
                fp,
            )

        return self

    async def _eject(self, bot: LatteMiad, guild_ids: Iterable[int] | None) -> None:
        await super()._eject(bot, guild_ids)

        # context menus in cog
        for method_name in dir(self):
            method = getattr(self, method_name)
            if context_values := getattr(method, '__context_menu__', None):
                if menu := context_values.get('context_menu_class'):
                    bot.tree.remove_command(menu.name, type=menu.type)
                    try:
                        self.__cog_context_menus__.remove(menu)
                    except ValueError:
                        pass

        # app commands localization
        translator = bot.translator
        if fp := self._get_file_path():
            await translator.save_to_files(
                [c.qualified_name for c in self.get_app_commands() if not c._guild_ids],  # exclude guild commands
                self.qualified_name,
                fp,
            )

        for app_command in self.get_app_commands():
            if app_command._guild_ids:
                continue
            translator.remove_app_command_localization(app_command)
