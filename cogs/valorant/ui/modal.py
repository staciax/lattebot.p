from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

import discord

# from async_lru import alru_cache
from discord import app_commands, ui

from core.i18n import I18n

if TYPE_CHECKING:
    from core.bot import LatteMaid

    from ..auth import RiotAuth

_ = I18n('valorant.ui.modal', Path(__file__).resolve().parent, read_only=True)


#  TODO: from base Modal
class RiotMultiFactorModal(ui.Modal, title=_('Two-factor authentication')):
    """Modal for riot login with multifactorial authentication"""

    def __init__(self, try_auth: RiotAuth, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__(timeout=120, custom_id='wait_for_modal')
        self.try_auth: RiotAuth = try_auth
        self.code: Optional[str] = None
        self.original_interaction: discord.Interaction[LatteMaid] = interaction
        self.interaction: Optional[discord.Interaction[LatteMaid]] = None
        self.two2fa = ui.TextInput(
            label=_('Input 2FA Code'),
            max_length=6,
            # min_length=6,
            style=discord.TextStyle.short,
            # custom_id=self.custom_id + '_2fa' + try_auth.puuid,  # TODO: + puuid
            placeholder=(
                _('You have 2FA enabled!')
                if self.try_auth.multi_factor_email is None
                else _('Riot sent a code to ') + self.try_auth.multi_factor_email
            ),
        )

        self.add_item(self.two2fa)

    async def on_submit(self, interaction: discord.Interaction[LatteMaid]) -> None:
        code = self.two2fa.value

        if not code:
            await interaction.response.send_message(_('Please input 2FA code'), ephemeral=True)
            return

        if not code.isdigit():
            await interaction.response.send_message(_('Invalid code'), ephemeral=True)
            return

        self.code = code
        self.interaction = interaction
        self.stop()

    async def on_error(self, interaction: discord.Interaction[LatteMaid], error: Exception) -> None:
        command = interaction.command or self.original_interaction.command
        if command is None:
            interaction.client.dispatch('modal_error', interaction, error, self)
            return
        if command._has_any_error_handlers():
            if isinstance(command, app_commands.Command):
                await command._invoke_error_handlers(interaction, error)  # type: ignore

        # Make sure we know what the error actually is
        # traceback.print_tb(error.__traceback__)
