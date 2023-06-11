from __future__ import annotations

import datetime

# import datetime
import random
from typing import TYPE_CHECKING, List, Optional, Union

from discord.utils import format_dt

import core.utils.chat_formatting as chat
import valorantx2 as valorantx
from core.utils.useful import MiadEmbed as Embed
from valorantx2 import RiotAuth
from valorantx2.emojis import VALORANT_POINT_EMOJI
from valorantx2.enums import Locale as ValorantLocale, MissionType, RelationType
from valorantx2.models import (  # MatchmakingRating,
    Agent,
    BonusStore,
    Buddy,
    BuddyLevel,
    BuddyLevelBundle,
    Bundle,
    BundleItemOffer,
    Contract,
    FeaturedBundle,
    Loadout,
    PlayerCard,
    PlayerCardBundle,
    PlayerTitle,
    PlayerTitleBundle,
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
    from valorantx2.models import RewardValorantAPI

BundleItem = Union[Skin, Buddy, Spray, PlayerCard, PlayerTitle]
FeaturedBundleItem = Union[SkinLevelBundle, BuddyLevelBundle, SprayBundle, PlayerCardBundle, PlayerTitleBundle]
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


def store_e(panel: SkinsPanelLayout, riot_id: str, *, locale: ValorantLocale = ValorantLocale.english) -> List[Embed]:
    embeds = [
        Embed(
            description='Daily store for {user}\n'.format(user=chat.bold(riot_id))
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

    if isinstance(item, PlayerTitle):
        item_icon = None
    elif isinstance(item, PlayerCard):
        item_icon = item.large_art
    elif isinstance(item, Spray):
        item_icon = item.animation_gif or item.full_transparent_icon or item.full_icon or item.display_icon
    else:
        item_icon = item.display_icon

    if item_icon is not None:
        embed.url = item_icon.url
        embed.set_thumbnail(url=item_icon)

    return embed


def wallet_e(wallet: Wallet, riot_id: str, *, locale: ValorantLocale) -> Embed:
    # vp = wallet.valorant_points
    # rad = wallet.radiant_points

    # vp_name = vp.name_localizations.from_locale(str(locale))

    embed = Embed(title=f'{riot_id} Point:').purple()

    # embed.add_field(
    #     name=f'{(vp_name if vp_name != "VP" else "Valorant")}',
    #     value=f'{vp.emoji} {wallet.valorant_points}',
    # )
    # embed.add_field(
    #     name=f'{rad.name_localizations.from_locale(str(locale)).removesuffix(" Points")}',
    #     value=f'{rad.emoji} {wallet.radiant_points}',
    # )
    return embed


def mission_e(
    contracts: valorantx.Contracts,
    riot_id: str,
    *,
    locale: ValorantLocale = ValorantLocale.american_english,
) -> Embed:
    daily = []
    weekly = []
    tutorial = []
    npe = []

    all_completed = True

    daily_format = '{0} | **+ {1.xp_grant:,} XP**\n- **`{1.current_progress}/{1.total_progress}`**'
    for mission in contracts.missions:
        title = mission.title.from_locale(locale)
        if mission.type == MissionType.daily:
            daily.append(daily_format.format(title, mission))
        elif mission.type == MissionType.weekly:
            weekly.append(daily_format.format(title, mission))
        elif mission.type == MissionType.tutorial:
            tutorial.append(daily_format.format(title, mission))
        elif mission.type == MissionType.npe:
            npe.append(daily_format.format(title, mission))

        if not mission.is_completed():
            all_completed = False

    embed = Embed(title=f'{riot_id} Mission:')
    if all_completed:
        embed.colour = 0x77DD77

    if len(daily) > 0:
        embed.add_field(
            name=f"**Daily**",
            value='\n'.join(daily),
            inline=False,
        )

    if len(weekly) > 0:
        embed.add_field(
            name=f"**Weekly**",
            value='\n'.join(weekly)
            + '\n\n Refill Time: {refill_time}'.format(
                refill_time=format_dt(
                    contracts.mission_metadata.weekly_refill_time.replace(tzinfo=datetime.timezone.utc), style='R'
                )
                if contracts.mission_metadata is not None and contracts.mission_metadata.weekly_refill_time is not None
                else '-'
            ),
        )

    if len(tutorial) > 0:
        embed.add_field(
            name=f"**Tutorial**",
            value='\n'.join(tutorial),
            inline=False,
        )

    if len(npe) > 0:
        embed.add_field(
            name=f"**NPE**",
            value='\n'.join(npe),
            inline=False,
        )

    return embed


def agent_e(agent: Agent, *, locale: valorantx.Locale = valorantx.Locale.american_english) -> Embed:
    embed = Embed(
        title=agent.display_name.from_locale(locale),
        description=chat.italics(agent.description.from_locale(locale)),
        colour=int(random.choice(agent.background_gradient_colors)[:-2], 16),
    ).purple()
    embed.set_image(url=agent.full_portrait)
    embed.set_thumbnail(url=agent.display_icon)
    embed.set_footer(
        text=agent.role.display_name.from_locale(locale),
        icon_url=agent.role.display_icon,
    )
    return embed


def buddy_e(buddy: Union[Buddy, BuddyLevel], *, locale: valorantx.Locale = valorantx.Locale.american_english) -> Embed:
    embed = Embed().purple()
    if isinstance(buddy, valorantx.Buddy):
        embed.set_author(
            name=buddy.display_name.from_locale(locale),
            icon_url=buddy.theme.display_icon if buddy.theme is not None else None,
            url=buddy.display_icon,
        )

    elif isinstance(buddy, valorantx.BuddyLevel):
        # assert buddy.parent is not None
        embed.set_author(
            name=buddy.parent.display_name.from_locale(locale),
            url=buddy.display_icon,
            icon_url=buddy.parent.theme.display_icon if buddy.parent.theme is not None else None,
        )
    embed.set_image(url=buddy.display_icon)

    return embed


def spray_e(spray: Union[Spray, SprayLevel], *, locale: valorantx.Locale = valorantx.Locale.american_english) -> Embed:
    embed = Embed().purple()

    if isinstance(spray, valorantx.Spray):
        embed.set_author(
            name=spray.display_name.from_locale(locale),
            url=spray.display_icon,
            icon_url=spray.theme.display_icon if spray.theme is not None else None,
        )
        embed.set_image(url=spray.animation_gif or spray.full_transparent_icon or spray.display_icon)

    elif isinstance(spray, valorantx.SprayLevel):
        # assert spray.parent is not None
        embed.set_author(
            name=spray.parent.display_name.from_locale(locale),
            icon_url=spray.parent.theme.display_icon if spray.parent.theme is not None else None,
            url=spray.display_icon,
        )
        embed.set_image(
            url=spray.parent.animation_gif
            or spray.parent.full_transparent_icon
            or spray.parent.display_icon
            or spray.display_icon
        )

    return embed


def player_card_e(
    player_card: valorantx.PlayerCard, *, locale: valorantx.Locale = valorantx.Locale.american_english
) -> Embed:
    embed = Embed().purple()
    embed.set_author(
        name=player_card.display_name.from_locale(locale),
        icon_url=player_card.theme.display_icon if player_card.theme is not None else None,
        url=player_card.large_art,
    )
    if player_card.large_art is not None:
        embed.set_image(url=player_card.large_art)
    return embed


def collection_front_e(
    loadout: Loadout,
    # mmr: MatchmakingRating,
    riot_id: str,
    *,
    locale: valorantx.Locale = valorantx.Locale.american_english,
) -> Embed:
    # latest_tier = mmr.get_latest_rank_tier() if mmr is not None else None

    embed = Embed()
    # e.description = '{vp_emoji} {wallet_vp} {rad_emoji} {wallet_rad}'.format(
    #     vp_emoji=wallet.get_valorant().emoji,  # type: ignore
    #     wallet_vp=wallet.valorant_points,
    #     rad_emoji=wallet.get_radiant().emoji,  # type: ignore
    #     wallet_rad=wallet.radiant_points,
    # )

    embed.set_author(
        name=f'{riot_id} - Collection',
        # icon_url=latest_tier.large_icon if latest_tier is not None else None,
    )
    embed.set_footer(text=f'Lv. {loadout.identity.account_level}')

    if loadout.identity.player_title is not None:
        embed.title = loadout.identity.player_title.text.from_locale(locale)

    if loadout.identity.player_card is not None:
        embed.set_image(url=loadout.identity.player_card.wide_art)
        # card_color_thief = await self.bot.get_or_fetch_colors(
        #     loadout.identity.player_card.uuid, loadout.identity.player_card.wide_art
        # )
        # embed.colour = random.choice(card_color_thief)

    return embed


def skin_loadout_e(gun: valorantx.Gun, *, locale: valorantx.Locale = valorantx.Locale.american_english) -> Embed:
    assert gun.skin_loadout is not None
    skin_name: str = gun.skin_loadout.display_name.from_locale(locale)
    if isinstance(gun.skin_loadout, valorantx.SkinChroma) and gun.skin_loadout.parent is not None:
        skin_name = gun.skin_loadout.parent.display_name.from_locale(locale)

    rarity = gun.skin_loadout.rarity

    embed = Embed(
        description=(rarity.emoji if rarity is not None else '')  # type: ignore
        + ' '
        + chat.bold(skin_name)
        + (' ★' if gun.skin_loadout.is_favorite() else ''),
        colour=int(rarity.highlight_color[0:6], 16) if rarity is not None else 0x0F1923,
    ).dark()

    embed.set_thumbnail(url=gun.skin_loadout.display_icon_fix)

    if gun.buddy_loadout is not None:
        buddy_name = gun.buddy_loadout.display_name.from_locale(locale)
        embed.set_footer(
            text=f'{buddy_name}' + (' ★' if gun.buddy_loadout.is_favorite() else ''),
            icon_url=gun.buddy_loadout.display_icon,
        )
    return embed


def spray_loadout_e(
    spray: Spray,
    slot: int,
    *,
    locale: valorantx.Locale = valorantx.Locale.american_english,
) -> Embed:
    spray_name = spray.display_name.from_locale(locale)
    embed = Embed(description=chat.bold(str(slot) + '. ' + spray_name.strip()) + (' ★' if spray.is_favorite() else ''))
    spray_icon = spray.animation_gif or spray.full_transparent_icon or spray.display_icon
    if spray_icon is not None:
        embed.set_thumbnail(url=spray_icon)
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
        # self.banner_embed: Embed = self.build_banner_embed()
        # self.item_embeds: List[Embed] = self._build_items_embeds()

    def build_banner_embed(self) -> Embed:
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
                            self.bundle.remaining_time_utc.replace(tzinfo=datetime.timezone.utc),
                            style='R',
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

    def build_items_embeds(self) -> List[Embed]:
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

    # def rebuild(self, locale: ValorantLocale) -> None:
    #     self.locale = locale
    #     self.banner_embed = self.build_banner_embed()
    #     self.item_embeds = self.build_items_embeds()


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
