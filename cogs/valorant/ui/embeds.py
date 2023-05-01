from __future__ import annotations

import datetime

# import datetime
# import random
from typing import TYPE_CHECKING, List, Optional, Union

from discord.utils import format_dt

import core.utils.chat_formatting as chat
from core.embed import Embed

from .. import valorantx3 as valorantx
from ..valorantx3 import RiotAuth
from ..valorantx3.emojis import VALORANT_POINT_EMOJI
from ..valorantx3.enums import Locale as ValorantLocale, RelationType
from ..valorantx3.models import (
    BonusStore,
    Buddy,
    BuddyLevel,
    BuddyLevelBundle,
    Bundle,
    BundleItemOffer,
    Contract,
    FeaturedBundle,
    PlayerCard,
    PlayerCardBundle,
    PlayerTitle,
    Skin,
    SkinChroma,
    SkinLevel,
    SkinLevelBonus,
    SkinLevelBundle,
    SkinLevelOffer,
    SkinsPanelLayout,
    Spray,
    SprayBundle,
    SprayLevel,
    Wallet,
)

if TYPE_CHECKING:
    from ..valorantx3.models import RewardValorantAPI

BundleItem = Union[Skin, Buddy, Spray, PlayerCard]
FeaturedBundleItem = Union[SkinLevelBundle, BuddyLevelBundle, SprayBundle, PlayerCardBundle]
SkinItem = Union[Skin, SkinLevel, SkinChroma]
SprayItem = Union[Spray, SprayLevel]
BuddyItem = Union[Buddy, BuddyLevel]

__all__ = (
    'BundleEmbed',
    'skin_e',
    'store_e',
    'select_featured_bundle_e',
    'select_featured_bundles_e',
    'bundle_item_e',
    'wallet_e',
)


def skin_e(
    skin: Union[valorantx.Skin, valorantx.SkinLevel, valorantx.SkinChroma, SkinLevelOffer, SkinLevelBonus],
    *,
    locale: ValorantLocale,
) -> Embed:
    embed = Embed(
        title=f"{skin.rarity.emoji} {chat.bold(skin.display_name_localized(locale))}",  # type: ignore
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


def store_e(
    panel: SkinsPanelLayout, riot_auth: RiotAuth, *, locale: ValorantLocale = ValorantLocale.english
) -> List[Embed]:
    embeds = [
        Embed(
            description='Daily store for {user}\n'.format(user=chat.bold(riot_auth.display_name))
            + f"Resets {format_dt(panel.remaining_time_utc.replace(tzinfo=datetime.timezone.utc), style='R')}",
        ).purple(),
    ]

    for skin in panel.skins:
        embeds.append(skin_e(skin, locale=locale))

    return embeds


def skin_e_hide(
    skin: SkinLevelBonus,
    *,
    locale: ValorantLocale,
) -> Embed:
    embed = Embed(title=' ').dark()

    if skin.rarity is not None:
        embed.colour = int(skin.rarity.highlight_color[0:6], 16)
        if skin.rarity.display_icon is not None:
            embed.title = skin.rarity.emoji  # type: ignore

    return embed


def nightmarket_front_e(bonus: BonusStore, riot_auth: RiotAuth, *, locale: ValorantLocale) -> Embed:
    embed = Embed(
        description=f'NightMarket for {chat.bold(riot_auth.display_name)}\n'
        f'Expires {format_dt(bonus.remaining_time_utc.replace(tzinfo=datetime.timezone.utc), style="R")}',
    ).purple()

    return embed


def select_featured_bundle_e(bundle: valorantx.FeaturedBundle, *, locale: ValorantLocale) -> Embed:
    embed = Embed(
        title=bundle.display_name_localized(locale),
        description=(
            f'{VALORANT_POINT_EMOJI} {chat.bold(str(bundle.discounted_cost))} - '
            f'expires {format_dt(bundle.remaining_time_utc.replace(tzinfo=datetime.timezone.utc), style="R")}'
        ),
        custom_id=bundle.uuid,
    )
    if bundle.extra_description is not None:
        embed.description = f'{chat.italics(bundle.extra_description.from_locale(locale))}\n' + (
            embed.description or ''
        )
    if bundle.display_icon_2 is not None:
        embed.set_thumbnail(url=bundle.display_icon_2.url)

    return embed


def select_featured_bundles_e(bundles: List[valorantx.FeaturedBundle], *, locale: ValorantLocale) -> List[Embed]:
    embeds = []
    for bundle in bundles:
        if bundle is None:
            continue
        embeds.append(select_featured_bundle_e(bundle, locale=locale))
    return embeds


def bundle_item_e(
    item: Union[BundleItem, FeaturedBundleItem],
    is_featured: bool = False,
    *,
    locale: ValorantLocale = ValorantLocale.american_english,
) -> Embed:
    emoji = item.rarity.emoji if isinstance(item, Skin) else ''  # type: ignore

    embed = Embed(
        title='{rarity} {name}'.format(rarity=emoji, name=chat.bold(item.display_name_localized(locale))),
        description=f'{VALORANT_POINT_EMOJI} ',
    ).dark()

    is_melee = item.is_melee() if hasattr(item, 'is_melee') and isinstance(item, SkinLevel) else False
    assert embed.description is not None
    if not is_featured or is_melee:
        embed.description += '{free} {price}'.format(
            free=(chat.bold('FREE') if is_featured else ''),
            price=(chat.strikethrough(str(item.cost)) if is_featured else item.cost),
        )
    else:
        assert isinstance(item, FeaturedBundleItem)
        if isinstance(item, BundleItemOffer) and (item.discounted_cost != item.cost) and (item.discounted_cost != 0):
            embed.description += f'{chat.bold(str(item.discounted_cost))} {chat.strikethrough(str(item.cost))}'
        else:
            embed.description += str(item.cost)

    if isinstance(item, PlayerCard):
        item_icon = item.large_art
    elif isinstance(item, Spray):
        item_icon = item.animation_gif or item.full_transparent_icon or item.full_icon or item.display_icon
    else:
        item_icon = item.display_icon

    if item_icon is not None:
        embed.url = item_icon.url
        embed.set_thumbnail(url=item_icon)

    return embed


class BundleEmbed:
    def __init__(
        self,
        bundle: Union[Bundle, FeaturedBundle],
        *,
        locale: ValorantLocale = ValorantLocale.american_english,
    ) -> None:
        self.bundle: Union[Bundle, FeaturedBundle] = bundle
        self.locale: ValorantLocale = locale

    def banner_embed(self) -> Embed:
        embed = Embed().purple()
        if self.bundle.display_icon_2 is not None:
            embed.set_image(url=self.bundle.display_icon_2.url)

        # TODO: i think if better way to do this
        if isinstance(self.bundle, valorantx.FeaturedBundle):
            embed.description = 'Featured Bundle: {bundle}\n{emoji} {price} {strikethrough} {expires}'.format(
                bundle=chat.bold(self.bundle.display_name_localized(self.locale) + ' Collection'),
                emoji=VALORANT_POINT_EMOJI,
                price=chat.bold(str(self.bundle.discounted_cost)),
                strikethrough=chat.strikethrough(str(self.bundle.cost)),
                expires=chat.italics(
                    '(Expires {expires})'.format(
                        expires=format_dt(
                            self.bundle.remaining_time_utc.replace(tzinfo=datetime.timezone.utc), style='R'
                        )
                    )
                ),
            )

        else:
            embed.description = 'Bundle: {bundle}\n{emoji} {price}'.format(
                bundle=chat.bold(self.bundle.display_name_localized(self.locale) + ' Collection'),
                emoji=VALORANT_POINT_EMOJI,
                price=self.bundle.cost,
            )

        return embed

    def item_embeds(self) -> List[Embed]:
        embeds = []

        def item_priorities(i: Union[BundleItem, FeaturedBundleItem]) -> int:
            is_melee = i.is_melee() if hasattr(i, 'is_melee') and isinstance(i, SkinLevel) else False
            if is_melee:
                return 0
            elif isinstance(i, SkinItem):
                return 1
            elif isinstance(i, BuddyItem):
                return 2
            elif isinstance(i, PlayerCard):
                return 3
            elif isinstance(i, SprayItem):
                return 4
            return 5

        for item in sorted(self.bundle.items, key=item_priorities):
            embeds.append(bundle_item_e(item, isinstance(self.bundle, FeaturedBundle), locale=self.locale))
        return embeds


def wallet_e(wallet: Wallet, riot_auth: RiotAuth, *, locale: ValorantLocale) -> Embed:
    # vp = wallet.valorant_points
    # rad = wallet.radiant_points

    # vp_name = vp.name_localizations.from_locale(str(locale))

    embed = Embed(title=f'{riot_auth.display_name} Point:').purple()

    # embed.add_field(
    #     name=f'{(vp_name if vp_name != "VP" else "Valorant")}',
    #     value=f'{vp.emoji} {wallet.valorant_points}',
    # )
    # embed.add_field(
    #     name=f'{rad.name_localizations.from_locale(str(locale)).removesuffix(" Points")}',
    #     value=f'{rad.emoji} {wallet.radiant_points}',
    # )
    return embed


class GamePassEmbed:
    def __init__(self, contract: Contract, riot_auth: RiotAuth, *, locale: ValorantLocale) -> None:
        self.contract: Contract = contract
        self.riot_auth: RiotAuth = riot_auth
        self.locale: ValorantLocale = locale
        self.title: str = ''  # TODO: localize
        if self.contract.content.relation_type is RelationType.agent:
            self.title = 'Agent'
        elif self.contract.content.relation_type is RelationType.season:
            self.title = 'Battlepass'
        elif self.contract.content.relation_type is RelationType.event:
            self.title = 'Eventpass'

    # @cache ?
    def build_page_embed(self, page: int, reward: RewardValorantAPI, locale: Optional[ValorantLocale] = None) -> Embed:
        locale = locale or self.locale
        embed = Embed(title=f'{self.title} for {self.riot_auth.display_name}')
        embed.set_footer(text=f'TIER {page + 1} | {self.contract.display_name_localized(locale)}')
        item = reward.get_item()
        if item is not None:
            embed.description = item.display_name_localized(locale)
            if not isinstance(item, PlayerTitle):
                if item.display_icon is not None:
                    if isinstance(item, SkinLevel):
                        embed.set_image(url=item.display_icon)
                    elif isinstance(item, PlayerCard):
                        embed.set_image(url=item.wide_art)
                    # elif isinstance(item, valorantx.Agent):
                    #     embed.set_image(url=item.full_portrait_v2 or item.full_portrait)
                    else:
                        embed.set_thumbnail(url=item.display_icon)
        return embed


# def game_pass_e(
#     reward: contract.Reward,
#     contract: contract.ContractU,
#     relation_type: valorantx.RelationType,
#     riot_auth: RiotAuth,
#     page: int,
#     *,
#     locale: Optional[ValorantLocale] = None,
# ) -> discord.Embed:

#     item = reward.get_item()

#     if relation_type is valorantx.RelationType.agent:
#         display_name = 'Agent'
#     elif relation_type is valorantx.RelationType.event:
#         display_name = 'Eventpass'
#     else:
#         display_name = 'Battlepass'
#     embed = discord.Embed(
#         title='{gamepass} for {display_name}'.format(gamepass=display_name, display_name=bold(riot_auth.display_name))
#     )
#     embed.set_footer(
#         text='TIER {tier} | {gamepass}'.format(
#             tier=page + 1, gamepass=contract.name_localizations.from_locale(str(locale))
#         )
#     )

#     if item is not None:
#         embed.description = '{item}'.format(item=item.display_name)
#         if not isinstance(item, valorantx.PlayerTitle):
#             if item.display_icon is not None:
#                 if isinstance(item, valorantx.SkinLevel):
#                     embed.set_image(url=item.display_icon)
#                 elif isinstance(item, valorantx.PlayerCard):
#                     embed.set_image(url=item.wide_icon)
#                 # elif isinstance(item, valorantx.Agent):
#                 #     embed.set_image(url=item.full_portrait_v2 or item.full_portrait)
#                 else:
#                     embed.set_thumbnail(url=item.display_icon)

#     return embed


# def mission_e(
#     contracts: valorantx.Contracts, riot_auth: RiotAuth, *, locale: Optional[ValorantLocale] = None
# ) -> discord.Embed:
#     daily = []
#     weekly = []
#     tutorial = []
#     npe = []

#     all_completed = True

#     daily_format = '{0} | **+ {1.xp:,} XP**\n- **`{1.progress}/{1.target}`**'
#     for mission in contracts.missions:
#         title = mission.title_localizations.from_locale(str(locale))
#         if mission.type == MissionType.daily:
#             daily.append(daily_format.format(title, mission))
#         elif mission.type == MissionType.weekly:
#             weekly.append(daily_format.format(title, mission))
#         elif mission.type == MissionType.tutorial:
#             tutorial.append(daily_format.format(title, mission))
#         elif mission.type == MissionType.npe:
#             npe.append(daily_format.format(title, mission))

#         if not mission.is_completed():
#             all_completed = False

#     embed = Embed(title='{display_name} Mission:'.format(display_name=riot_auth.display_name))
#     if all_completed:
#         embed.colour = 0x77DD77

#     if len(daily) > 0:
#         embed.add_field(
#             name=f"**Daily**",
#             value='\n'.join(daily),
#             inline=False,
#         )

#     if len(weekly) > 0:

#         embed.add_field(
#             name=f"**Weekly**",
#             value='\n'.join(weekly)
#             + '\n\n Refill Time: {refill_time}'.format(
#                 refill_time=format_relative(contracts.mission_metadata.weekly_refill_time)
#                 if contracts.mission_metadata.weekly_refill_time is not None
#                 else '-'
#             ),
#         )

#     if len(tutorial) > 0:
#         embed.add_field(
#             name=f"**Tutorial**",
#             value='\n'.join(tutorial),
#             inline=False,
#         )

#     if len(npe) > 0:
#         embed.add_field(
#             name=f"**NPE**",
#             value='\n'.join(npe),
#             inline=False,
#         )

#     return embed
