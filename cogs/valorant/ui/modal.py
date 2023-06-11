from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord

# from async_lru import alru_cache
from discord import ui

from core.i18n import _

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2 import RiotAuth


#  TODO: from base Modal
class RiotMultiFactorModal(ui.Modal, title=_('Two-factor authentication')):
    """Modal for riot login with multifactorial authentication"""

    def __init__(self, try_auth: RiotAuth) -> None:
        super().__init__(timeout=120, custom_id='wait_for_modal')
        self.try_auth: RiotAuth = try_auth
        self.code: Optional[str] = None
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
        interaction.client.dispatch('modal_error', interaction, error, self)
        # Make sure we know what the error actually is
        # traceback.print_tb(error.__traceback__)
