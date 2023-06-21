from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from core.i18n import I18n

from .abc import MixinMeta

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__name__)


_ = I18n('valorant.error', __file__, read_only=True)


class ErrorHandler(MixinMeta):
    async def cog_app_command_error(
        self,
        interaction: discord.Interaction[LatteMaid],
        error: app_commands.AppCommandError,
    ) -> None:
        await super().cog_app_command_error(interaction, error)  # type: ignore
