from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

# i18n
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import dynamic_cooldown

from core.checks import cooldown_medium
from core.cog import context_menu
from core.i18n import I18n

from .abc import MixinMeta

if TYPE_CHECKING:
    from core.bot import LatteMaid


_log = logging.getLogger(__name__)


_ = I18n('valorant.context_menu', __file__, read_only=True)

SUPPORT_GUILD_ID = 1097859504906965042


class ContextMenu(MixinMeta):
    @context_menu(name=_T('party invite'), guilds=[discord.Object(id=SUPPORT_GUILD_ID)])
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

        # gamename, _, tagline = message.content.partition('#')

        # async with self.valorant_client.lock:
        #     party_player = await self.valorant_client.http.get_party_player()
        #     await self.valorant_client.http.post_party_invite_by_display_name(
        #         party_player['CurrentPartyID'],
        #         gamename,
        #         tagline,
        #     )

        await interaction.response.send_message('Not implemented yet.', ephemeral=True)
