from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

import discord
from discord import Interaction, ui
from discord.app_commands import CheckFailure
from discord.ext import commands

from ..errors import CheckFailure, ComponentOnCooldown
from ..i18n import _

# from .ui import interaction_error_handler

if TYPE_CHECKING:
    from bot import LatteMaid
    from discord import InteractionMessage, Message
    from typing_extensions import Self


_log = logging.getLogger(__name__)


def key(interaction: discord.Interaction) -> Union[discord.User, discord.Member]:
    return interaction.user


class Button(ui.Button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    # TODO: something?


# thanks stella_bot # https://github.com/InterStella0/stella_bot/blob/master/utils/buttons.py
class BaseView(ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._message: Optional[Union[Message, InteractionMessage]] = None

    def reset_timeout(self) -> None:
        self.timeout = self.timeout

    async def _scheduled_task(self, item: discord.ui.Item, interaction: Interaction):
        try:
            item._refresh_state(interaction, interaction.data)  # type: ignore

            allow = await self.interaction_check(interaction)
            if not allow:
                return await self.on_check_failure(interaction)

            if self.timeout:
                self.__timeout_expiry = time.monotonic() + self.timeout

            await item.callback(interaction)
        except Exception as e:
            return await self.on_error(interaction, e, item)

    async def on_error(self, interaction: Interaction, error: Exception, item: ui.Item[Any]) -> None:
        interaction.client.dispatch('view_error', interaction, error, item)
        # return await interaction_error_handler(interaction, error)

    # --- code from pycord ---

    async def on_check_failure(self, interaction: Interaction) -> None:
        """coro

        A callback that is called when the interaction check fails.

        Parameters
        ----------
        interaction: Interaction
            The interaction that failed the check.
        """
        pass

    def disable_all_items(self, *, exclusions: Optional[List[ui.Item]] = None) -> Self:
        """
        Disables all items in the view.

        Parameters
        ----------
        exclusions: Optional[List[ui.Item]]
            A list of items in `self.children` to not disable from the view.
        """
        for child in self.children:
            if exclusions is not None or child not in exclusions:
                child.disabled = True
        return self

    def enable_all_items(self, *, exclusions: Optional[List[ui.Item]] = None) -> Self:
        """
        Enables all items in the view.

        Parameters
        ----------
        exclusions: Optional[List[ui.Item]]
            A list of items in `self.children` to not enable from the view.
        """
        for child in self.children:
            if exclusions is not None or child not in exclusions:
                child.disabled = False
        return self

    # --- end of code from pycord ---

    def disable_items(self, cls: Optional[Type[ui.Item]] = None) -> Self:
        for item in self.children:
            if cls is not None:
                if isinstance(item, cls):
                    item.disabled = True
        return self

    def remove_item_by_type(self, *, cls: Optional[Type[ui.Item]] = None) -> Self:
        for item in self.children:
            if cls is not None:
                if isinstance(item, cls):
                    self.remove_item(item)
        return self

    def disable_buttons(self) -> Self:
        return self.disable_items(ui.Button)

    def disable_selects(self) -> Self:
        return self.disable_items(ui.Select)

    def add_items(self, *items: ui.Item) -> Self:
        for item in items:
            self.add_item(item)
        return self

    @property
    def message(self) -> Optional[Union[Message, InteractionMessage]]:
        return self._message

    @message.setter
    def message(self, value: Optional[Union[Message, InteractionMessage]]) -> None:
        self._message = value


# thanks stella_bot
class ViewAuthor(BaseView):
    def __init__(self, interaction: Interaction[LatteMaid], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.interaction: Interaction[LatteMaid] = interaction
        self.locale: discord.Locale = interaction.locale
        self.bot: LatteMaid = interaction.client
        self._author: Union[discord.Member, discord.User] = interaction.user
        # self.is_command = interaction.command is not None
        self.cooldown = commands.CooldownMapping.from_cooldown(3.0, 10.0, key)
        self.cooldown_user = commands.CooldownMapping.from_cooldown(1.0, 8.0, key)

    async def interaction_check(self, interaction: Interaction[LatteMaid]) -> bool:
        """Only allowing the context author to interact with the view"""

        user = interaction.user

        if await self.bot.is_owner(user):
            return True

        if isinstance(user, discord.Member) and user.guild_permissions.administrator:
            return True

        if user != self.author:
            return False

        self.locale = interaction.locale

        bucket = self.cooldown.get_bucket(interaction)
        if bucket is not None:
            if bucket.update_rate_limit():
                raise ComponentOnCooldown(bucket, interaction)

        return True

    async def on_check_failure(self, interaction: Interaction[LatteMaid]) -> None:
        """Handles the error when the check fails"""

        bucket = self.cooldown_user.get_bucket(interaction)
        if bucket is not None:
            if bucket.update_rate_limit():
                raise ComponentOnCooldown(bucket, interaction)

        if interaction.command is not None:
            app_cmd_name = interaction.command.qualified_name
            app_cmd = self.bot.get_app_command(app_cmd_name)
            app_cmd_text = f'{app_cmd.mention}' if app_cmd is not None else f'/`{app_cmd_name}`'
            content = _("Only {author} can use this. If you want to use it, use {app_cmd}").format(
                author=self.author.mention, app_cmd=app_cmd_text
            )
        else:
            content = _("Only `{author}` can use this.").format(author=self.author.mention)

        raise CheckFailure(content)

    @property
    def author(self) -> Union[discord.Member, discord.User]:
        return self._author

    @author.setter
    def author(self, value: Union[discord.Member, discord.User]) -> None:
        self._author = value
