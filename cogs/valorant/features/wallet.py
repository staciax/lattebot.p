from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from cogs.valorant.features.base import ValorantPageSource
from core.bot import LatteMaid
from core.ui.embed import MiadEmbed as Embed

from ..utils import locale_converter
from .base import BaseView, ValorantPageSource

# fmt: off
__all__ = (
    'WalletView',
)
# fmt: on

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2.models import Wallet

    from ..auth import RiotAuth


def wallet_e(wallet: Wallet, riot_id: str, *, locale: discord.Locale) -> Embed:
    vlocale = locale_converter.to_valorant(locale)

    embed = Embed(title=f'{riot_id} Point:').purple()

    vp_display_name = 'Valorant'
    if vp := wallet.get_valorant_currency():
        vp_display_name = vp.display_name.from_locale(vlocale)
        if vp_display_name.lower() == 'vp':
            vp_display_name = 'Valorant'
        vp_display_name = vp.emoji + ' ' + vp_display_name  # type: ignore

    rad_display_name = 'Radiant'
    if rad := wallet.get_radiant_currency():
        rad_display_name = rad.display_name.from_locale(vlocale)
        rad_display_name = rad.emoji + ' ' + rad_display_name.replace('Points', '').replace('Point', '')  # type: ignore

    knd_display_name = 'Kingdom'
    if knd := wallet.get_kingdom_currency():
        knd_display_name = knd.display_name.from_locale(vlocale)

    embed.add_field(
        name=vp_display_name,
        value=f'{wallet.valorant_points}',
    )
    embed.add_field(
        name=rad_display_name,
        value=f'{wallet.radiant_points}',
    )
    embed.add_field(
        name=knd_display_name,
        value=f'{wallet.kingdom_points}',
    )
    return embed


class WalletPageSource(ValorantPageSource):
    async def format_page_valorant(self, view: BaseView, page: int, riot_auth: RiotAuth) -> Embed:
        wallet = await view.valorant_client.fetch_wallet(riot_auth)
        embed = wallet_e(
            wallet,
            riot_id=riot_auth.riot_id,
            locale=view.locale,
        )
        return embed


class WalletView(BaseView):
    def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__(interaction, WalletPageSource())
