from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union

import discord
from discord import app_commands
from discord.ext import commands

from core.i18n import I18n, cog_i18n

from .ui import application_error_handler

if TYPE_CHECKING:
    from discord.ui import Item, Modal

    from core.bot import LatteMaid

_ = I18n('errors', __file__)

_log = logging.getLogger(__file__)


@cog_i18n(_)
class Errors(commands.Cog, name='errors'):
    """Developer commands"""

    def __init__(self, bot: LatteMaid) -> None:
        self.bot = bot

    @commands.Cog.listener('on_app_command_error')
    async def on_app_command_error(
        self, interaction: discord.Interaction[LatteMaid], error: Union[Exception, app_commands.errors.AppCommandError]
    ) -> None:
        await application_error_handler(interaction, error)

    @commands.Cog.listener('on_view_error')
    async def on_view_error(self, interaction: discord.Interaction[LatteMaid], error: Exception, item: Item) -> None:
        interaction.extras['item'] = item
        await application_error_handler(interaction, error)

    @commands.Cog.listener('on_modal_error')
    async def on_modal_error(self, interaction: discord.Interaction[LatteMaid], error: Exception, modal: Modal) -> None:
        interaction.extras['modal'] = modal
        await application_error_handler(interaction, error)
