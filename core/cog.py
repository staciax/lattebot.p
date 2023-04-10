from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, Iterable, List, Optional, TypeVar, Union

import discord
from discord import Interaction, app_commands
from discord.app_commands import ContextMenu, Group, locale_str
from discord.ext import commands
from discord.utils import MISSING

if TYPE_CHECKING:
    from typing_extensions import Self

    from .bot import LatteMaid

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


# https://github.com/InterStella0/stella_bot/blob/bf5f5632bcd88670df90be67b888c282c6e83d99/utils/cog.py#L28
def context_menu(
    *,
    name: Union[str, locale_str] = MISSING,
    nsfw: bool = False,
    guilds: List[discord.abc.Snowflake] = MISSING,
    auto_locale_strings: bool = True,
    extras: Dict[Any, Any] = MISSING,
) -> Callable[[ContextMenuCallback], ContextMenu]:
    def inner(func: Any) -> Any:
        nonlocal name
        func.__context_menu_guilds__ = guilds
        name = func.__name__.title() if name is MISSING else name
        func.__context_menu__ = dict(
            name=name,
            nsfw=nsfw,
            auto_locale_strings=auto_locale_strings,
            extras=extras,
        )
        return func

    return inner


class LatteMaidCog(commands.Cog):
    async def _inject(
        self,
        bot: LatteMaid,
        override: bool,
        guild: Optional[discord.abc.Snowflake],
        guilds: List[discord.abc.Snowflake],
    ) -> Self:
        await super()._inject(bot, override, guild, guilds)
        for method_name in dir(self):
            method = getattr(self, method_name)
            if context_values := getattr(method, "__context_menu__", None):
                menu = app_commands.ContextMenu(callback=method, **context_values)
                context_values["context_menu_class"] = menu
                bot.tree.add_command(menu, guilds=method.__context_menu_guilds__)

        return self

    async def _eject(self, bot: LatteMaid, guild_ids: Optional[Iterable[int]]) -> None:
        await super()._eject(bot, guild_ids)
        for method_name in dir(self):
            method = getattr(self, method_name)
            if context_values := getattr(method, "__context_menu__", None):
                if menu := context_values.get("context_menu_class"):
                    bot.tree.remove_command(menu.name, type=menu.type)
