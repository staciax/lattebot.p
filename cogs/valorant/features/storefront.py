from __future__ import annotations

import logging
from datetime import timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord import ui
from discord.utils import format_dt

import core.utils.chat_formatting as chat
from cogs.valorant.features.base import ValorantPageSource
from core.bot import LatteMaid
from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from valorantx2.emojis import KINGDOM_CREDIT_EMOJI, VALORANT_POINT_EMOJI
from valorantx2.models import (
    AccessoryStore,
    AccessoryStoreOffer,
    BonusStore,
    BuddyLevel,
    PlayerCard,
    PlayerTitle,
    SkinLevelBonus,
    SkinLevelOffer,
    SkinsPanelLayout,
    Spray,
)

from ..utils import locale_converter
from .base import BaseView, ValorantPageSource

__all__ = (
    'StoreFrontView',
    'NightMarketView',
)

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2.models import Skin, SkinChroma, SkinLevel

    from ..auth import RiotAuth


_log = logging.getLogger(__name__)

_ = I18n('valorant.features.storefront', Path(__file__).resolve().parent, read_only=True)


# ShooterGame/Content/RecruitmentData/Cable_RecruitmentData.uasset
# RECRUITMENT_END_DATE_TICKS = 638259156000000000
# RECRUITMENT_MILESTONE_THRESHOLD = 200_000
# def store_agents_recruitment_e(
#     agent: Agent,
#     recruitment_progress: RecruitmentProgressUpdate | None,
#     riot_id: str,
#     *,
#     locale: discord.Locale = discord.american_english,
# ) -> Embed:
#     valorant_locale = locale_converter.to_valorant(locale)
#     embed = Embed(
#         colour=int(random.choice(agent.background_gradient_colors)[:-2], 16),
#         # description=chat.bold(f'{agent.display_name_localized(valorant_locale)}\n'),
#     ).purple()
#     embed.set_author(name=f'Agent Recruiment Event')
#     embed.set_thumbnail(url=agent.display_icon)
#     embed.set_image(url=agent.full_portrait_v2)
#     embed.set_footer(text=riot_id)

#     # unlock

#     if recruitment_progress is None:
#         unlock_value = '0 / {0:,} XP'.format(RECRUITMENT_MILESTONE_THRESHOLD)
#     else:
#         unlock_value = '{0.progress_after:,} / {0.milestone_threshold:,} XP'.format(recruitment_progress)

#     end_date = datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=RECRUITMENT_END_DATE_TICKS / 10)
#     if datetime.datetime.now() < end_date:
#         unlock_value += f'\nEnds {format_dt(end_date.replace(tzinfo=datetime.timezone.utc), style="R")}\n'

#     embed.add_field(
#         name='UNLOCK: ' + chat.bold(f'{agent.display_name_localized(valorant_locale)}\n'),
#         value=unlock_value,
#     )

#     # recruit

#     new_agent_note = (
#         chat.bold('NOTE: ')
#         + ' '
#         + chat.italics(
#             'For the first 28 days, new Agents can only be unlocked using VP or you can unlock them by earning XP during the Agent Recruitment Event.'
#         )
#     )

#     embed.add_field(
#         name='RECRUIT',
#         value=f'{VALORANT_POINT_EMOJI} 1,000\n{KINGDOM_CREDIT_EMOJI} 8,000\n{new_agent_note}',
#         inline=False,
#     )

#     return embed


def skin_e(
    skin: Skin | SkinLevel | SkinChroma | SkinLevelOffer | SkinLevelBonus,
    *,
    locale: discord.Locale,
) -> Embed:
    valorant_locale = locale_converter.to_valorant(locale)
    embed = Embed(
        title=f"{skin.rarity.emoji} {chat.bold(skin.display_name_localized(valorant_locale))}",  # type: ignore
    ).purple()

    if isinstance(skin, SkinLevelOffer):
        embed.description = f'{VALORANT_POINT_EMOJI} {chat.bold(str(skin.cost))}'
    elif isinstance(skin, SkinLevelBonus):
        embed.description = (
            f'{VALORANT_POINT_EMOJI} {chat.bold(str(skin.discount_costs))}\n'
            f'{VALORANT_POINT_EMOJI} {chat.strikethrough(str(skin.price))} (-{skin.discount_percent}%)'
        )

    if skin.display_icon is not None:
        embed.url = skin.display_icon.url
        embed.set_thumbnail(url=skin.display_icon)

    if skin.rarity is not None:
        embed.colour = int(skin.rarity.highlight_color[0:6], 16)

    return embed


def store_featured_e(
    panel: SkinsPanelLayout, riot_id: str, *, locale: discord.Locale = discord.Locale.american_english
) -> list[Embed]:
    embeds = [
        Embed(
            description='Daily store // {user}\n'.format(user=chat.bold(riot_id))
            + f'Resets {format_dt(panel.remaining_time_utc.replace(tzinfo=timezone.utc), style="R")}',
        ).purple(),
    ]

    for skin in panel.skins:
        embeds.append(skin_e(skin, locale=locale))

    return embeds


# def skin_e_hide(skin: SkinLevelBonus) -> Embed:
#     embed = Embed().empty_title().dark()

#     if skin.rarity is None:
#         return embed

#     embed.colour = int(skin.rarity.highlight_color[0:6], 16)
#     if skin.rarity.display_icon is not None:
#         embed.title = skin.rarity.emoji
#     return embed


def nightmarket_front_e(bonus: BonusStore, riot_id: str, *, locale: discord.Locale) -> Embed:
    embed = Embed(
        description=f'NightMarket // {chat.bold(riot_id)}\n'
        f'Expires {format_dt(bonus.remaining_time_utc.replace(tzinfo=timezone.utc), style="R")}',
    ).purple()

    return embed


def accessory_e(store_offer: AccessoryStoreOffer, *, locale: discord.Locale = discord.Locale.american_english) -> Embed:
    valorant_locale = locale_converter.to_valorant(locale)

    accessory = store_offer.offer

    embed = Embed()
    embed.description = f'{KINGDOM_CREDIT_EMOJI} {chat.bold(str(accessory.cost))}'

    for reward in accessory.rewards:
        if reward.item is None:
            _log.warning(f'No item for reward id: {reward.id} type: {reward.type}')
            continue

        embed.title = reward.item.display_name_localized(valorant_locale)

        if isinstance(reward.item, (Spray, BuddyLevel)):
            if reward.item.display_icon is not None:
                embed.url = reward.item.display_icon.url
                embed.set_thumbnail(url=reward.item.display_icon)
        elif isinstance(reward.item, PlayerCard):
            if reward.item.large_art is not None:
                embed.url = reward.item.large_art.url
                embed.set_thumbnail(url=reward.item.large_art)
        elif isinstance(reward.item, PlayerTitle):
            player_title_icon_url = 'https://cdn.discordapp.com/attachments/417245049315655690/1123541013072457728/valorant_player_title_icon.png'
            embed.url = player_title_icon_url
            embed.set_thumbnail(url=player_title_icon_url)

    if store_offer.contract is not None:
        embed.set_footer(text=store_offer.contract.display_name_localized(valorant_locale))
    return embed


def store_accessories_e(
    store: AccessoryStore, riot_id: str, *, locale: discord.Locale = discord.Locale.american_english
) -> list[Embed]:
    embeds = [
        Embed(
            description='Weekly Accessories // {user}\n'.format(user=chat.bold(riot_id))
            + f'Resets {format_dt(store.remaining_time_utc.replace(tzinfo=timezone.utc), style="R")}',
        ).purple(),
    ]
    for offer in store.offers:
        embeds.append(accessory_e(offer, locale=locale))

    return embeds


class StoreFrontPageSource(ValorantPageSource):
    async def format_page_valorant(self, view: BaseView, page: int, riot_auth: RiotAuth) -> list[Embed]:
        storefront = await view.valorant_client.fetch_storefront(riot_auth)
        if page == 0:  # featured
            embeds = store_featured_e(
                storefront.skins_panel_layout,
                riot_id=riot_auth.riot_id,
                locale=view.locale,
            )
        elif page == 1:  # accessories
            embeds = store_accessories_e(
                storefront.accessory_store,
                riot_id=riot_auth.riot_id,
                locale=view.locale,
            )
        else:
            embeds = [Embed(description=_('Page not found', view.locale))]
        return embeds


class NightMarketPageSource(ValorantPageSource):
    async def format_page_valorant(self, view: BaseView, page: int, riot_auth: RiotAuth) -> list[Embed]:
        storefront = await view.valorant_client.fetch_storefront(riot_auth)
        if storefront.bonus_store is None:
            return [Embed(description=_('Nightmarket is not available', view.locale))]
        embeds = [nightmarket_front_e(storefront.bonus_store, riot_auth.riot_id, locale=view.locale)]
        embeds += [skin_e(skin, locale=view.locale) for skin in storefront.bonus_store.skins]
        return embeds


class StoreFrontView(BaseView):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        # source: ValorantPageSource = discord.utils.MISSING,
    ) -> None:
        super().__init__(interaction, StoreFrontPageSource())
        self.current_page: int = 0

    async def _get_kwargs_from_valorant_page(self, page: int) -> dict[str, Any]:
        kwargs = await super()._get_kwargs_from_valorant_page(page)
        self.current_page = page
        return kwargs

    @ui.button(label='Featured', disabled=True)
    async def featured(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
        await interaction.response.defer()
        if self.message is None:
            return
        button.disabled = True
        self.accessories.disabled = False
        kwargs = await self._get_kwargs_from_valorant_page(0)
        await self.message.edit(**kwargs, view=self)

    @ui.button(label='Accessories')
    async def accessories(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
        await interaction.response.defer()
        if self.message is None:
            return
        button.disabled = True
        self.featured.disabled = False
        kwargs = await self._get_kwargs_from_valorant_page(1)
        await self.message.edit(**kwargs, view=self)


class NightMarketView(BaseView):
    def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__(interaction, NightMarketPageSource())
