from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import discord
from discord import Interaction, ui
from discord.ext import commands

from core.bot import LatteMaid

from ..errors import CheckFailure, ComponentOnCooldown

if TYPE_CHECKING:
    from bot import LatteMaid
    from discord import InteractionMessage, Message
    from typing_extensions import Self


_log = logging.getLogger(__name__)


def key(interaction: discord.Interaction) -> discord.User | discord.Member:
    return interaction.user


class Button(ui.Button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    # TODO: something?


# thanks stella_bot # https://github.com/InterStella0/stella_bot/blob/master/utils/buttons.py
class BaseView(ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._message: Message | InteractionMessage | None = None

    def reset_timeout(self) -> None:
        self.timeout = self.timeout

    async def before_callback(self, interaction: Interaction[LatteMaid]) -> None:
        """A callback that is called before the callback is called."""
        pass

    async def after_callback(self, interaction: Interaction[LatteMaid]) -> None:
        """A callback that is called after the callback is called."""
        pass

    async def _scheduled_task(self, item: discord.ui.Item, interaction: Interaction[LatteMaid]):
        try:
            item._refresh_state(interaction, interaction.data)  # type: ignore

            allow = await self.interaction_check(interaction)  # await item.interaction_check(interaction) and
            if not allow:
                return await self.on_check_failure(interaction)

            if self.timeout:
                self.__timeout_expiry = time.monotonic() + self.timeout

            await self.before_callback(interaction)
            await item.callback(interaction)
            await self.after_callback(interaction)
        except Exception as e:
            return await self.on_error(interaction, e, item)

    async def on_error(self, interaction: Interaction, error: Exception, item: ui.Item[Any]) -> None:
        interaction.client.dispatch('view_error', interaction, error, item)

    @staticmethod
    async def safe_edit_message(
        message: discord.Message | discord.InteractionMessage, **kwargs: Any
    ) -> discord.Message | discord.InteractionMessage | None:
        try:
            new_message = await message.edit(**kwargs)
        except (discord.errors.HTTPException, discord.errors.Forbidden):
            return None
        else:
            return new_message

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

    def disable_all_items(self, *, exclusions: list[ui.Button | ui.Select] = []) -> Self:
        """
        Disables all items in the view.

        Parameters
        ----------
        exclusions: Optional[List[ui.Item]]
            A list of items in `self.children` to not disable from the view.
        """
        for child in self.children:
            if isinstance(child, (ui.Button, ui.Select)) and child in exclusions:
                child.disabled = True
        return self

    def enable_all_items(self, *, exclusions: list[ui.Button | ui.Select] = []) -> Self:
        """
        Enables all items in the view.

        Parameters
        ----------
        exclusions: Optional[List[ui.Item]]
            A list of items in `self.children` to not enable from the view.
        """
        for child in self.children:
            if isinstance(child, (ui.Button, ui.Select)) and child in exclusions:
                child.disabled = False
        return self

    def url_button(self, label: str, url: str, *, emoji: str | None = None, disabled: bool = False) -> Self:
        """
        Adds a url button to the view.

        Parameters
        ----------
        label: str
            The label of the button.
        url: str
            The url of the button.
        disabled: bool
            Whether the button is disabled or not.
        """

        self.add_item(ui.Button(label=label, url=url, emoji=emoji, disabled=disabled))
        return self

    # --- end of code from pycord ---

    def disable_items(self) -> Self:
        for child in self.children:
            if isinstance(child, (ui.Button, ui.Select)):
                child.disabled = True
        return self

    def remove_item_by_type(self, cls_: Any) -> Self:
        for item in self.children:
            if isinstance(item, Any):
                self.remove_item(item)
        return self

    def disable_buttons(self) -> Self:
        for child in self.children:
            if isinstance(child, ui.Button):
                child.disabled = True
        return self

    def disable_selects(self) -> Self:
        for child in self.children:
            if isinstance(child, ui.Select):
                child.disabled = True
        return self

    def add_items(self, *items: ui.Item) -> Self:
        for item in items:
            self.add_item(item)
        return self

    @property
    def message(self) -> Message | InteractionMessage | None:
        return self._message

    @message.setter
    def message(self, value: Message | InteractionMessage | None) -> None:
        self._message = value


# thanks stella_bot
class ViewAuthor(BaseView):
    def __init__(self, interaction: Interaction[LatteMaid], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.interaction: Interaction[LatteMaid] = interaction
        self.locale: discord.Locale = interaction.locale
        self.bot: LatteMaid = interaction.client
        self._author: discord.Member | discord.User = interaction.user
        # self.is_command = interaction.command is not None
        self.cooldown = commands.CooldownMapping.from_cooldown(3.0, 10.0, key)
        self.cooldown_user = commands.CooldownMapping.from_cooldown(1.0, 8.0, key)

    async def before_callback(self, interaction: Interaction[LatteMaid]) -> None:
        if self.locale == interaction.locale:
            return
        self.locale = interaction.locale

    async def interaction_check(self, interaction: Interaction[LatteMaid]) -> bool:
        """Only allowing the context author to interact with the view"""

        user = interaction.user

        if await self.bot.is_owner(user):
            return True

        # if isinstance(user, discord.Member) and user.guild_permissions.administrator:
        #     return True

        if user != self.author:
            return False

        if bucket := self.cooldown.get_bucket(interaction):
            if bucket.update_rate_limit():
                raise ComponentOnCooldown(bucket, bucket.get_retry_after())

        return True

    async def on_check_failure(self, interaction: Interaction[LatteMaid]) -> None:
        """Handles the error when the check fails"""
        command = interaction.command or self.interaction.command
        raise CheckFailure(command, self.author)

    @property
    def author(self) -> discord.Member | discord.User:
        return self._author

    @author.setter
    def author(self, value: discord.Member | discord.User) -> None:
        self._author = value
