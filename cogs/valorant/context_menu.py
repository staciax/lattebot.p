from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

# i18n
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import dynamic_cooldown

from core.checks import cooldown_medium
from core.cog import context_menu

from .abc import MixinMeta

if TYPE_CHECKING:
    from core.bot import LatteMaid


_log = logging.getLogger(__name__)


class ContextMenu(MixinMeta):
    @context_menu(name=_T('party invite'))
    @dynamic_cooldown(cooldown_medium)
    async def message_invite_to_party(
        self,
        interaction: discord.Interaction[LatteMaid],
        message: discord.Message,
    ) -> None:
        """Invite the author of the message to the party."""
        if '#' in message.content:
            await interaction.response.send_message('Not implemented yet.', ephemeral=True)
            return
        await interaction.response.send_message('Not implemented yet.', ephemeral=True)
