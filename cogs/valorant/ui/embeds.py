from __future__ import annotations

import datetime
import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

from discord import Locale as DiscordLocale
from discord.utils import format_dt

import core.utils.chat_formatting as chat
import valorantx2 as valorantx
from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from valorantx2.emojis import KINGDOM_CREDIT_EMOJI, VALORANT_POINT_EMOJI
from valorantx2.enums import GameModeURL, MissionType, RelationType, RoundResultCode
from valorantx2.models import (
    AccessoryStore,
    AccessoryStoreOffer,
    Buddy,
    BuddyLevel,
    BuddyLevelBundle,
    Bundle,
    BundleItemOffer,
    FeaturedBundle,
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
    Spray,
    SprayBundle,
    SprayLevel,
)
from valorantx2.utils import locale_converter

from . import utils

if TYPE_CHECKING:
    from valorantx2.models import (
        Agent,
        BonusStore,
        Contract,
        Loadout,
        MatchPlayer,
        RewardValorantAPI,
        SkinsPanelLayout,
        Wallet,
    )
    from valorantx2.models.custom.match import MatchDetails

__all__ = (
    'BundleEmbed',
    'skin_e',
    'store_featured_e',
    'select_featured_bundle_e',
    'select_featured_bundles_e',
    'bundle_item_e',
    'wallet_e',
)

BundleItem = Union[Skin, Buddy, Spray, PlayerCard, PlayerTitle]
FeaturedBundleItem = Union[SkinLevelBundle, BuddyLevelBundle, SprayBundle, PlayerCardBundle, PlayerTitleBundle]
SkinItem = Union[Skin, SkinLevel, SkinChroma]
SprayItem = Union[Spray, SprayLevel]
BuddyItem = Union[Buddy, BuddyLevel]

_ = I18n('valorant.ui.embeds', Path(__file__).resolve().parent, read_only=True)
_log = logging.getLogger(__name__)


def skin_e(
    skin: Union[Skin, SkinLevel, SkinChroma, SkinLevelOffer, SkinLevelBonus],
    *,
    locale: DiscordLocale,
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
    panel: SkinsPanelLayout, riot_id: str, *, locale: DiscordLocale = DiscordLocale.american_english
) -> List[Embed]:
    embeds = [
        Embed(
            description='Daily store for {user}\n'.format(user=chat.bold(riot_id))
            + f'Resets {format_dt(panel.remaining_time_utc.replace(tzinfo=datetime.timezone.utc), style="R")}',
        ).purple(),
    ]

    for skin in panel.skins:
        embeds.append(skin_e(skin, locale=locale))

    return embeds


def accessory_e(store_offer: AccessoryStoreOffer, *, locale: DiscordLocale = DiscordLocale.american_english) -> Embed:
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
    store: AccessoryStore, riot_id: str, *, locale: DiscordLocale = DiscordLocale.american_english
) -> List[Embed]:
    embeds = [
        Embed(
            description='Weekly Accessories for {user}\n'.format(user=chat.bold(riot_id))
            + f'Resets {format_dt(store.remaining_time_utc.replace(tzinfo=datetime.timezone.utc), style="R")}',
        ).purple(),
    ]
    for offer in store.offers:
        embeds.append(accessory_e(offer, locale=locale))

    return embeds


def skin_e_hide(skin: SkinLevelBonus) -> Embed:
    embed = Embed().empty_title().dark()

    if skin.rarity is None:
        return embed

    embed.colour = int(skin.rarity.highlight_color[0:6], 16)
    if skin.rarity.display_icon is not None:
        embed.title = skin.rarity.emoji  # type: ignore

    return embed


def nightmarket_front_e(bonus: BonusStore, riot_id: str, *, locale: DiscordLocale) -> Embed:
    embed = Embed(
        description=f'NightMarket for {chat.bold(riot_id)}\n'
        f'Expires {format_dt(bonus.remaining_time_utc.replace(tzinfo=datetime.timezone.utc), style="R")}',
    ).purple()

    return embed


def select_featured_bundle_e(bundle: valorantx.FeaturedBundle, *, locale: DiscordLocale) -> Embed:
    valorant_locale = locale_converter.to_valorant(locale)
    embed = Embed(
        title=bundle.display_name_localized(valorant_locale),
        description=(
            f'{VALORANT_POINT_EMOJI} {chat.bold(str(bundle.discounted_cost))} - '
            f'expires {format_dt(bundle.remaining_time_utc.replace(tzinfo=datetime.timezone.utc), style="R")}'
        ),
        custom_id=bundle.uuid,
    )
    if bundle.extra_description is not None:
        embed.description = f'{chat.italics(bundle.extra_description.from_locale(valorant_locale))}\n' + (
            embed.description or ''
        )
    if bundle.display_icon_2 is not None:
        embed.set_thumbnail(url=bundle.display_icon_2.url)

    return embed


def select_featured_bundles_e(bundles: List[valorantx.FeaturedBundle], *, locale: DiscordLocale) -> List[Embed]:
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
    locale: DiscordLocale = DiscordLocale.american_english,
) -> Embed:
    valorant_locale = locale_converter.to_valorant(locale)

    emoji = item.rarity.emoji if isinstance(item, Skin) else ''  # type: ignore
    embed = Embed(
        title='{rarity} {name}'.format(rarity=emoji, name=chat.bold(item.display_name_localized(valorant_locale))),
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
            embed.description += chat.bold(str(item.discounted_cost)) + ' '
            if item.discounted_cost != item.cost:
                embed.description += chat.strikethrough(str(item.cost))
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


def wallet_e(wallet: Wallet, riot_id: str, *, locale: DiscordLocale) -> Embed:
    valorant_locale = locale_converter.to_valorant(locale)

    embed = Embed(title=f'{riot_id} Point:').purple()

    vp_display_name = 'Valorant'
    if vp := wallet.get_valorant_currency():
        vp_display_name = vp.display_name.from_locale(valorant_locale)
        if vp_display_name.lower() == 'vp':
            vp_display_name = 'Valorant'
        vp_display_name = vp.emoji + ' ' + vp_display_name  # type: ignore

    rad_display_name = 'Radiant'
    if rad := wallet.get_radiant_currency():
        rad_display_name = rad.display_name.from_locale(valorant_locale)
        rad_display_name = rad.emoji + ' ' + rad_display_name.replace('Points', '').replace('Point', '')  # type: ignore

    knd_display_name = 'Kingdom'
    if knd := wallet.get_kingdom_currency():
        knd_display_name = knd.display_name.from_locale(valorant_locale)
        knd_display_name = knd.emoji + ' ' + knd_display_name.replace('Point', '')  # type: ignore

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


def mission_e(
    contracts: valorantx.Contracts,
    riot_id: str,
    *,
    locale: DiscordLocale = DiscordLocale.american_english,
) -> Embed:
    valorant_locale = locale_converter.to_valorant(locale)

    daily = []
    weekly = []
    tutorial = []
    npe = []

    all_completed = True

    daily_format = '{0} | **+ {1.xp_grant:,} XP**\n- **`{1.current_progress}/{1.total_progress}`**'
    for mission in contracts.missions:
        title = mission.title.from_locale(valorant_locale)
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


def player_card_e(player_card: PlayerCard, *, locale: valorantx.Locale = valorantx.Locale.american_english) -> Embed:
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
    #     vp_emoji=wallet.get_valorant().emoji,
    #     wallet_vp=wallet.valorant_points,
    #     rad_emoji=wallet.get_radiant().emoji,
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


# patch note embed


def patch_note_e(pn: valorantx.PatchNote, banner_url: Optional[str] = None) -> Embed:
    embed = Embed(
        title=pn.title,
        timestamp=pn.timestamp.replace(tzinfo=datetime.timezone.utc),
        url=pn.url,
        description=chat.italics(pn.description),
    )
    embed.set_image(url=(banner_url or pn.banner))
    return embed


# bundle embed


class BundleEmbed:
    def __init__(
        self,
        bundle: Union[Bundle, FeaturedBundle],
        *,
        locale: DiscordLocale = DiscordLocale.american_english,
    ) -> None:
        self.bundle: Union[Bundle, FeaturedBundle] = bundle
        self.locale: DiscordLocale = locale
        # self.banner_embed: Embed = self.build_banner_embed()
        # self.item_embeds: List[Embed] = self._build_items_embeds()

    def build_banner_embed(self) -> Embed:
        valorant_locale = locale_converter.to_valorant(self.locale)

        embed = Embed().purple()
        if self.bundle.display_icon_2 is not None:
            embed.set_image(url=self.bundle.display_icon_2.url)

        # TODO: i think if better way to do this
        if isinstance(self.bundle, valorantx.FeaturedBundle):
            embed.description = 'Featured Bundle: {bundle}\n{emoji} {price} {strikethrough} {expires}'.format(
                bundle=chat.bold(self.bundle.display_name_localized(valorant_locale) + ' Collection'),
                emoji=VALORANT_POINT_EMOJI,
                price=chat.bold(str(self.bundle.discounted_cost)),
                strikethrough=chat.strikethrough(str(self.bundle.cost))
                if self.bundle.discounted_cost != self.bundle.cost
                else '',
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
                bundle=chat.bold(self.bundle.display_name_localized(valorant_locale) + ' Collection'),
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


# gamepass embed


class GamePassEmbed:
    def __init__(self, contract: Contract, riot_id: str, *, locale: DiscordLocale) -> None:
        self.contract: Contract = contract
        self.riot_id: str = riot_id
        self.locale: DiscordLocale = locale
        self.title: str = ''  # TODO: localize
        if self.contract.content.relation_type is RelationType.agent:
            self.title = 'Agent'
        elif self.contract.content.relation_type is RelationType.season:
            self.title = 'Battlepass'
        elif self.contract.content.relation_type is RelationType.event:
            self.title = 'Eventpass'

    # @cache ?
    def build_page_embed(self, page: int, reward: RewardValorantAPI, locale: Optional[DiscordLocale] = None) -> Embed:
        locale = locale or self.locale

        valorant_locale = locale_converter.to_valorant(locale)

        embed = Embed(title=f'{self.title} for {self.riot_id}')
        embed.set_footer(text=f'TIER {page + 1} | {self.contract.display_name_localized(valorant_locale)}')
        item = reward.get_item()
        if item is not None:
            embed.description = item.display_name_localized(valorant_locale)
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


# match history


def match_history_select_e(
    match: MatchDetails,
    puuid: str,
    *,
    locale: valorantx.Locale = valorantx.Locale.american_english,
) -> Embed:
    me = match.get_player(puuid)
    if me is None:
        return Embed(description='You are not in this match.').warning()

    agent = me.agent
    game_mode = match.match_info.game_mode
    match_map = match.match_info.map
    tier = me.competitive_tier

    left_team_score, right_team_score = utils.find_match_score_by_player(match, me)
    result = utils.get_match_result_by_player(match, me)

    embed = Embed(
        # title=match.game_mode.emoji + ' ' + match.game_mode.display_name,
        description="{kda} {kills}/{deaths}/{assists}".format(
            # tier=((tier.emoji + ' ') if match.match_info.queue_id == 'competitive' else ''),
            kda=chat.bold('KDA'),
            kills=me.stats.kills,
            deaths=me.stats.deaths,
            assists=me.stats.assists,
        ),
        timestamp=match.started_at,
    )

    if me.is_winner() and not match.is_draw():
        embed.info()
    elif match.is_draw():
        embed.light()
    else:
        embed.danger()

    # elif not me.is_winner() and not match.is_draw():
    #     embed.danger()

    # if game_mode is not None:
    #     embed.title = game_mode.emoji + ' ' + game_mode.display_name.from_locale(locale)

    embed.set_author(
        name=f'{result} {left_team_score} - {right_team_score}',
        icon_url=agent.display_icon if agent is not None else None,
    )

    if match_map is not None and match_map.splash is not None and game_mode is not None:
        embed.set_thumbnail(url=match_map.splash)

        if gamemode_name_override := getattr(match.match_info.game_mode, 'display_name_override', None):
            if callable(gamemode_name_override):
                gamemode_name_override(match.match_info.is_ranked())

        embed.set_footer(
            text=f'{game_mode.display_name.from_locale(locale)} • {match_map.display_name.from_locale(locale)}',
            icon_url=tier.large_icon
            if tier is not None and match.match_info.queue_id == 'competitive'
            else game_mode.display_icon,
        )
    return embed


# match details embed
# below is so fk ugly code but i don't have any idea to make it better :(
# but it works so i don't care
# if only desktop version, i can make it better but both desktop and mobile version is so fk ugly code


class MatchDetailsEmbed:
    def __init__(self, match: MatchDetails):
        self.match = match

    def __template_e(
        self,
        player: MatchPlayer,
        performance: bool = False,
        *,
        locale: valorantx.Locale = valorantx.Locale.american_english,
    ) -> Embed:
        match = self.match
        match_map = match.match_info.map
        gamemode = match.match_info.game_mode
        left_team_score, right_team_score = utils.find_match_score_by_player(match, player)
        result = utils.get_match_result_by_player(match, player)

        embed = Embed(
            title='{mode} {map} - {won}:{lose}'.format(
                mode=gamemode.emoji if gamemode is not None else '',  # type: ignore
                map=match_map.display_name.from_locale(locale) if match_map is not None else match.match_info.map_id,
                won=left_team_score,
                lose=right_team_score,
            ),
            timestamp=match.started_at,
        )

        embed.set_author(
            name='{author} - {page}'.format(
                author=player.display_name,
                page=(
                    gamemode.display_name.from_locale(locale) if gamemode is not None and not performance else 'Performance'
                ),
            ),
            icon_url=player.agent.display_icon_small if player.agent is not None else None,
        )

        embed.set_footer(text=result)

        if player.is_winner() and not match.is_draw():
            embed.info()
        elif match.is_draw():
            embed.light()
        else:
            embed.danger()

        return embed

    # desktop

    def __build_page_1_d(
        self,
        match: MatchDetails,
        player: MatchPlayer,
        *,
        locale: valorantx.Locale,
    ) -> Embed:
        embed = self.__template_e(player, locale=locale)
        members = sorted(match.get_members(player), key=lambda p: p.stats.acs, reverse=True)
        opponents = sorted(match.get_opponents(player), key=lambda p: p.stats.acs, reverse=True)
        if match.match_info._game_mode_url != GameModeURL.deathmatch.value:
            # MY TEAM
            myteam = '\n'.join([self.__display_player(player, p) for p in members])

            # page 1
            embed.add_field(
                name='MY TEAM',
                value=myteam,
            )
            embed.add_field(
                name='ACS',
                value="\n".join([self.__display_acs(p) for p in members]),
            )
            embed.add_field(name='KDA', value="\n".join([str(p.stats.kda) for p in members]))

            # ENEMY TEAM
            enemyteam = '\n'.join([self.__display_player(player, p, bold=False) for p in opponents])

            # page 1
            embed.add_field(
                name='ENEMY TEAM',
                value=enemyteam,
            )
            embed.add_field(
                name='ACS',
                value="\n".join([self.__display_acs(p) for p in opponents]),
            )
            embed.add_field(name='KDA', value="\n".join([str(p.stats.kda) for p in opponents]))

            # page 2

        else:
            players = sorted(self.match.players, key=lambda p: p.stats.score, reverse=True)
            embed.add_field(
                name='Players',
                value='\n'.join([self.__display_player(player, p) for p in players]),
            )
            embed.add_field(name='SCORE', value='\n'.join([f'{p.stats.score}' for p in players]))
            embed.add_field(name='KDA', value='\n'.join([f'{p.stats.kda}' for p in players]))

        timelines = []

        for i, r in enumerate(self.match.round_results, start=1):
            if i == 12:
                timelines.append(' | ')

            timelines.append(r.emoji_by_player(player))

            if r.round_result_code == RoundResultCode.surrendered.value:
                break

        if match.match_info._game_mode_url not in [GameModeURL.escalation.value, GameModeURL.deathmatch.value]:
            if len(timelines) > 25:
                embed.add_field(name='Timeline:', value=''.join(timelines[:25]), inline=False)
                embed.add_field(name='Overtime:', value=''.join(timelines[25:]), inline=False)
            else:
                embed.add_field(name='Timeline:', value=''.join(timelines), inline=False)

        return embed

    def __build_page_2_d(
        self,
        match: MatchDetails,
        player: MatchPlayer,
        *,
        locale: valorantx.Locale,
    ) -> Embed:
        embed = self.__template_e(player, locale=locale)
        members = sorted(match.get_members(player), key=lambda p: p.stats.acs, reverse=True)
        opponents = sorted(match.get_opponents(player), key=lambda p: p.stats.acs, reverse=True)

        # MY TEAM
        embed.add_field(
            name='MY TEAM',
            value='\n'.join([self.__display_player(player, p) for p in members]),
        )
        embed.add_field(name='FK', value="\n".join([str(p.stats.first_kills) for p in members]))
        embed.add_field(
            name='HS%',
            value='\n'.join([(str(round(p.stats.head_shot_percent, 1)) + '%') for p in members]),
        )

        # ENEMY TEAM
        embed.add_field(
            name='ENEMY TEAM',
            value='\n'.join([self.__display_player(player, p, bold=False) for p in opponents]),
        )
        embed.add_field(name='FK', value='\n'.join([str(p.stats.first_kills) for p in opponents]))
        embed.add_field(
            name='HS%',
            value='\n'.join([(str(round(p.stats.head_shot_percent, 1)) + '%') for p in opponents]),
        )

        return embed

    def __build_page_3_d(
        self,
        player: MatchPlayer,
        *,
        locale: valorantx.Locale,
    ) -> Embed:
        embed = self.__template_e(player, performance=True, locale=locale)
        embed.add_field(
            name='KDA',
            value='\n'.join(
                [
                    p.kda
                    for p in sorted(
                        player.get_opponents_stats(),
                        key=lambda p: p.opponent.display_name.lower(),
                    )
                ]
            ),
        )
        embed.add_field(
            name='Opponent',
            value='\n'.join(
                self.__display_player(player, p.opponent)
                for p in sorted(
                    player.get_opponents_stats(),
                    key=lambda p: p.opponent.display_name.lower(),
                )
            ),
        )

        text = self.__display_abilities(player)
        if text != '':
            embed.add_field(name='Abilities', value=text, inline=False)

        return embed

    # def __build_death_match_d(
    #     self,
    #     match: MatchDetails,
    #     player: MatchPlayer,
    #     *,
    #     locale: valorantx.Locale,
    # ) -> Embed:
    #     embed = Embed()

    #     players = sorted(match.players, key=lambda p: p.stats.score, reverse=True)
    #     embed.set_author(
    #         name=match.match_info.game_mode.display_name.from_locale(locale)
    #         if match.match_info.game_mode is not None
    #         else None,
    #         icon_url=player.agent.display_icon if player.agent is not None else None,
    #     )
    #     embed.add_field(
    #         name='Players',
    #         value='\n'.join([self.__display_player(player, p) for p in players]),
    #     )
    #     embed.add_field(name='SCORE', value='\n'.join([f'{p.stats.score}' for p in players]))
    #     embed.add_field(name='KDA', value='\n'.join([f'{p.stats.kda}' for p in players]))
    #     return embed

    # mobile

    def __build_page_1_m(self, match: MatchDetails, player: MatchPlayer, *, locale: valorantx.Locale) -> Embed:
        embed = self.__template_e(player, locale=locale)

        members = sorted(match.get_members(player), key=lambda p: p.stats.acs, reverse=True)
        opponents = sorted(match.get_opponents(player), key=lambda p: p.stats.acs, reverse=True)

        if match.match_info._game_mode_url != GameModeURL.deathmatch.value:
            # MY TEAM
            embed.add_field(name='\u200b', value=chat.bold('MY TEAM'), inline=False)
            for p in members:
                embed.add_field(
                    name=self.__display_player(player, p),
                    value=f'ACS: {self.__display_acs(p)}\nKDA: {p.stats.kda}',
                    inline=True,
                )

            # ENEMY TEAM
            embed.add_field(name='\u200b', value=chat.bold('ENEMY TEAM'), inline=False)
            for p in opponents:
                embed.add_field(
                    name=self.__display_player(player, p),
                    value=f'ACS: {self.__display_acs(p)}\nKDA: {p.stats.kda}',
                    inline=True,
                )
        else:
            players = sorted(match.players, key=lambda p: p.stats.score, reverse=True)
            for p in players:
                embed.add_field(
                    name=self.__display_player(player, p),
                    value=f'SCORE: {p.stats.score}\nKDA: {p.stats.kda}',
                    inline=True,
                )

        timelines = []

        for i, r in enumerate(match.round_results, start=1):
            # if r.result_code == valorantx.RoundResultCode.surrendered:
            #     timelines.append('Surrendered')
            #     break

            if i == 12:
                timelines.append(' | ')

            timelines.append(r.emoji_by_player(player))

        if match.match_info._game_mode_url not in [GameModeURL.escalation.value, GameModeURL.deathmatch.value]:
            # TODO: __contains__ is not implemented for GameModeType
            if len(timelines) > 25:
                embed.add_field(name='Timeline:', value=''.join(timelines[:25]), inline=False)
                embed.add_field(name='Overtime:', value=''.join(timelines[25:]), inline=False)
            else:
                embed.add_field(name='Timeline:', value=''.join(timelines), inline=False)

        return embed

    def __build_page_2_m(self, match: MatchDetails, player: MatchPlayer, *, locale: valorantx.Locale) -> Embed:
        embed = self.__template_e(player, locale=locale)

        members = sorted(match.get_members(player), key=lambda p: p.stats.acs, reverse=True)
        opponents = sorted(match.get_opponents(player), key=lambda p: p.stats.acs, reverse=True)

        # MY TEAM
        embed.add_field(name='\u200b', value=chat.bold('MY TEAM'))
        for p in members:
            embed.add_field(
                name=self.__display_player(player, p),
                value=f'FK: {p.stats.first_kills}\nHS%: {round(p.stats.head_shot_percent, 1)}%',
                inline=True,
            )

        # ENEMY TEAM
        embed.add_field(name='\u200b', value=chat.bold('ENEMY TEAM'), inline=False)
        for p in opponents:
            embed.add_field(
                name=self.__display_player(player, p, bold=False),
                value=f'FK: {p.stats.first_kills}\nHS%: {round(p.stats.head_shot_percent, 1)}%',
                inline=True,
            )

        return embed

    def __build_page_3_m(self, player: MatchPlayer, *, locale: valorantx.Locale) -> Embed:
        embed = self.__template_e(player, performance=True, locale=locale)
        embed.add_field(
            name='KDA Opponent',
            value='\n'.join(
                [(p.kda + ' ' + self.__display_player(player, p.opponent)) for p in player.get_opponents_stats()]
            ),
        )

        text = self.__display_abilities(player)
        if text != '':
            embed.add_field(name='Abilities', value=text, inline=False)

        return embed

    # def __build_death_match_m(
    #     self,
    #     match: MatchDetails,
    #     player: MatchPlayer,
    #     *,
    #     locale: valorantx.Locale,
    # ) -> Embed:
    #     embed = Embed()

    #     players = sorted(match.players, key=lambda p: p.stats.score, reverse=True)
    #     embed.set_author(
    #         name=match.match_info.game_mode.display_name.from_locale(locale)
    #         if match.match_info.game_mode is not None
    #         else None,
    #         icon_url=player.agent.display_icon if player.agent is not None else None,
    #     )
    #     for p in players:
    #         embed.add_field(
    #             name=self.__display_player(player, p),
    #             value=f'SCORE: {p.stats.score}\nKDA: {p.stats.kda}',
    #             inline=True,
    #         )

    #     return embed

    # display

    def __display_player(self, player: MatchPlayer, other_player: MatchPlayer, *, bold: bool = True) -> str:
        def display_tier(player: MatchPlayer) -> str:
            tier = player.competitive_tier
            return (
                (' ' + tier.emoji + ' ')  # type: ignore
                if self.match.match_info.queue_id == 'competitive' and tier is not None
                else ''
            )

        text = (
            other_player.agent.emoji  # type: ignore
            + display_tier(other_player)
            + ' '
            + (chat.bold(other_player.display_name) if bold and other_player == player else other_player.display_name)
        )

        return text

    def __display_acs(self, player: MatchPlayer, star: bool = True) -> str:
        def display_mvp(player: MatchPlayer) -> str:
            if player == self.match.match_mvp:
                return '★'
            elif player == self.match.team_mvp:
                return '☆'
            return ''

        acs = str(int(player.stats.acs))
        if star:
            acs += ' ' + display_mvp(player)
        return acs

    def __display_abilities(self, player: MatchPlayer) -> str:
        abilities = player.stats.ability_casts
        if abilities is None:
            return ''

        return '{c_emoji} {c_casts} {q_emoji} {q_casts} {e_emoji} {e_casts} {x_emoji} {x_casts}'.format(
            c_emoji=abilities.c.emoji,  # type: ignore
            c_casts=round(abilities.c_casts / player.stats.rounds_played, 1),
            e_emoji=abilities.e.emoji,  # type: ignore
            e_casts=round(abilities.e_casts / player.stats.rounds_played, 1),
            q_emoji=abilities.q.emoji,  # type: ignore
            q_casts=round(abilities.q_casts / player.stats.rounds_played, 1),
            x_emoji=abilities.x.emoji,  # type: ignore
            x_casts=round(abilities.x_casts / player.stats.rounds_played, 1),
        )

    # build

    def build(
        self,
        puuid: str,
        *,
        locale: valorantx.Locale = valorantx.Locale.american_english,
    ) -> Tuple[List[Embed], List[Embed]]:
        player = self.match.get_player(puuid)
        if player is None:
            raise ValueError(f'player {puuid} was not in this match')

        # desktop

        desktops = [
            self.__build_page_1_d(self.match, player, locale=locale),
            # self.__build_page_2_d(self.match, player, locale=locale),
            self.__build_page_3_d(player, locale=locale),
        ]

        # mobile

        mobiles = [
            self.__build_page_1_m(self.match, player, locale=locale),
            # self.__build_page_2_m(self.match, player, locale=locale),
            self.__build_page_3_m(player, locale=locale),
        ]

        # performance
        if self.match.match_info._game_mode_url != GameModeURL.deathmatch.value:
            desktops.insert(1, self.__build_page_2_d(self.match, player, locale=locale))
            mobiles.insert(1, self.__build_page_2_m(self.match, player, locale=locale))

        return desktops, mobiles
