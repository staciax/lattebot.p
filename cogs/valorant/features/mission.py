from __future__ import annotations

from datetime import timezone
from typing import TYPE_CHECKING

import discord
from discord.utils import format_dt

from cogs.valorant.features.base import ValorantPageSource
from core.bot import LatteMaid
from core.ui.embed import MiadEmbed as Embed
from valorantx2.enums import MissionType

from ..utils import locale_converter
from .base import BaseView, ValorantPageSource

# fmt: off
__all__ = (
    'MissionView',
)
# fmt: on

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2.models import Contracts, DailyTicket

    from ..auth import RiotAuth


def mission_e(
    contracts: Contracts,
    daily_ticket: DailyTicket,
    riot_id: str,
    *,
    locale: discord.Locale = discord.Locale.american_english,
) -> Embed:
    vlocale = locale_converter.to_valorant(locale)

    daily = []
    weekly = []
    tutorial = []
    npe = []
    all_completed = True

    # daily
    for milestone in sorted(daily_ticket.daily_rewards.milestones, key=lambda x: x.bonus_applied):
        daily.append('✅' if milestone.bonus_applied else '❌')

    # weekly, tutorial, npe
    mission_format = '{0} | **+ {1.xp_grant:,} XP**\n- **`{1.current_progress}/{1.total_progress}`**'
    for mission in contracts.missions:
        title = mission.title.from_locale(vlocale)
        # if mission.type == MissionType.daily:
        #     daily.append(daily_format.format(title, mission))
        if mission.type == MissionType.weekly:
            weekly.append(mission_format.format(title, mission))
        elif mission.type == MissionType.tutorial:
            tutorial.append(mission_format.format(title, mission))
        elif mission.type == MissionType.npe:
            npe.append(mission_format.format(title, mission))

        if not mission.is_completed():
            all_completed = False

    embed = Embed(title=f'{riot_id} Mission:')
    if all_completed:
        embed.colour = 0x77DD77

    if len(daily) > 0:
        embed.add_field(
            name='**Daily**',
            value=' - '.join(daily),
            inline=False,
        )

    if len(weekly) > 0:
        embed.add_field(
            name=f'**Weekly**',
            value='\n'.join(weekly)
            + '\n\n Refill Time: {refill_time}'.format(
                refill_time=format_dt(
                    contracts.mission_metadata.weekly_refill_time.replace(tzinfo=timezone.utc), style='R'
                )
                if contracts.mission_metadata is not None and contracts.mission_metadata.weekly_refill_time is not None
                else '-'
            ),
        )

    if len(tutorial) > 0:
        embed.add_field(
            name=f'**Tutorial**',
            value='\n'.join(tutorial),
            inline=False,
        )

    if len(npe) > 0:
        embed.add_field(
            name='**NPE**',
            value='\n'.join(npe),
            inline=False,
        )

    return embed


class MissionPageSource(ValorantPageSource):
    async def format_page_valorant(self, view: BaseView, page: int, riot_auth: RiotAuth) -> Embed:
        contracts = await view.valorant_client.fetch_contracts(riot_auth)
        daily_ticket = await view.valorant_client.fetch_daily_ticket(renew=True, riot_auth=riot_auth)
        embed = mission_e(contracts, daily_ticket, riot_auth.riot_id, locale=view.locale)
        return embed


class MissionView(BaseView):
    def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__(interaction, MissionPageSource())
