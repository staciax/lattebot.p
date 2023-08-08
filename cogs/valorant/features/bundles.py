from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any, TypeAlias

import discord
from discord import ui
from discord.utils import format_dt

import core.utils.chat_formatting as chat
from core.ui.embed import MiadEmbed as Embed
from core.ui.views import ViewAuthor
from core.utils.pages import LattePages, ListPageSource
from valorantx2.emojis import VALORANT_POINT_EMOJI
from valorantx2.models import (
    Buddy,
    BuddyLevel,
    BuddyLevelBundle,
    BundleItemOffer,
    FeaturedBundle,
    PlayerCard,
    PlayerCardBundle,
    PlayerTitle,
    PlayerTitleBundle,
    Skin,
    SkinChroma,
    SkinLevel,
    SkinLevelBundle,
    Spray,
    SprayBundle,
    SprayLevel,
)

from ..utils import locale_converter

# fmt: off
__all__ = (
    'FeaturedBundleView',
)
# fmt: on


if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2.models import Bundle

    BundleItem = Skin | Buddy | Spray | PlayerCard | PlayerTitle

FeaturedBundleItem: TypeAlias = SkinLevelBundle | BuddyLevelBundle | SprayBundle | PlayerCardBundle | PlayerTitleBundle
SkinItem: TypeAlias = Skin | SkinLevel | SkinChroma
SprayItem: TypeAlias = Spray | SprayLevel
BuddyItem: TypeAlias = Buddy | BuddyLevel


_log = logging.getLogger(__name__)


def select_featured_bundle_e(bundle: FeaturedBundle, *, locale: discord.Locale) -> Embed:
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
    if bundle.display_icon is not None:
        embed.set_thumbnail(url=bundle.display_icon.url)

    return embed


def select_featured_bundles_e(bundles: list[FeaturedBundle], *, locale: discord.Locale) -> list[Embed]:
    embeds = []
    for bundle in bundles:
        if bundle is None:
            continue
        embeds.append(select_featured_bundle_e(bundle, locale=locale))
    return embeds


def bundle_item_e(
    item: BundleItem | FeaturedBundleItem,
    is_featured: bool = False,
    *,
    locale: discord.Locale = discord.Locale.american_english,
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


class BundleEmbed:
    def __init__(
        self,
        bundle: Bundle | FeaturedBundle,
        *,
        locale: discord.Locale = discord.Locale.american_english,
    ) -> None:
        self.bundle: Bundle | FeaturedBundle = bundle
        self.locale: discord.Locale = locale
        # self.banner_embed: Embed = self.build_banner_embed()
        # self.item_embeds: List[Embed] = self._build_items_embeds()

    def build_banner_embed(self) -> Embed:
        valorant_locale = locale_converter.to_valorant(self.locale)

        embed = Embed().purple()
        if self.bundle.display_icon_2 is not None:
            embed.set_image(url=self.bundle.display_icon_2.url)

        # TODO: i think if better way to do this
        if isinstance(self.bundle, FeaturedBundle):
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

    def build_items_embeds(self) -> list[Embed]:
        embeds = []

        def item_priorities(i: BundleItem | FeaturedBundleItem) -> int:
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


class FeaturedBundlePageSource(ListPageSource['Embed']):
    def __init__(self, bundle: FeaturedBundle, locale: discord.Locale) -> None:
        self.bundle: FeaturedBundle = bundle
        self.locale: discord.Locale = locale
        self.bundle_embed = BundleEmbed(bundle, locale=self.locale)
        self.embed: Embed = self.bundle_embed.build_banner_embed()
        super().__init__(self.bundle_embed.build_items_embeds(), per_page=5)

    async def format_page(self, menu: FeaturedBundlePageView, entries: list[Embed]) -> list[Embed]:
        entries.insert(0, self.embed)
        return entries

    def rebuild(self, locale: discord.Locale) -> None:
        _log.debug(f'rebuilding bundle embeds with locale {locale}')
        self.locale = locale
        self.bundle_embed.locale = self.locale
        self.entries = self.bundle_embed.build_items_embeds()
        self.embed = self.bundle_embed.build_banner_embed()


class FeaturedBundlePageView(LattePages):
    source: FeaturedBundlePageSource

    def __init__(self, source: FeaturedBundlePageSource, *, interaction: discord.Interaction[LatteMaid], **kwargs):
        super().__init__(source, interaction=interaction, check_embeds=True, compact=True, **kwargs)

    async def interaction_check(self, interaction: discord.Interaction[LatteMaid], /) -> bool:
        if await super().interaction_check(interaction):
            if self.source.locale != interaction.locale:
                self.source.rebuild(interaction.locale)
            return True
        return False

    async def start(self) -> None:
        # self.message = await self.interaction.original_response()
        return await super().start()


class FeaturedBundleButton(ui.Button['FeaturedBundleView']):
    def __init__(self, label: str, uuid: str, **kwargs: Any) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.blurple, **kwargs)
        self.uuid: str = uuid

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        self.view.selected = True

        await interaction.response.defer()
        bundle = self.view.bundles[self.uuid]
        source = FeaturedBundlePageSource(bundle, locale=interaction.locale)
        view = FeaturedBundlePageView(source, interaction=self.view.interaction)
        view.message = self.view.message
        await view.start()


class FeaturedBundleView(ViewAuthor):
    def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__(interaction)
        self.selected: bool = False
        self.bundles: dict[str, FeaturedBundle] = {}

    def build_buttons(self, bundles: list[FeaturedBundle]) -> None:
        for index, bundle in enumerate(bundles, start=1):
            self.add_item(
                FeaturedBundleButton(
                    label=str(index) + '. ' + bundle.display_name_localized(),
                    uuid=bundle.uuid,
                )
            )

    async def start(self) -> None:
        bundles = await self.bot.valorant_client.fetch_featured_bundle()
        self.bundles = {bundle.uuid: bundle for bundle in bundles if bundle is not None}

        if len(self.bundles) > 1:
            self.build_buttons(list(self.bundles.values()))
            embeds = select_featured_bundles_e(
                list(self.bundles.values()),
                locale=self.locale,
            )
            self.message = await self.interaction.followup.send(embeds=embeds, view=self)
        elif len(self.bundles) == 1:
            source = FeaturedBundlePageSource(self.bundles[list(self.bundles.keys())[0]], locale=self.interaction.locale)
            view = FeaturedBundlePageView(source, interaction=self.interaction)
            await view.start()
        else:
            _log.error(
                f'user {self.interaction.user}({self.interaction.user.id}) tried to get featured bundles without bundles'
            )
            raise ValueError('No featured bundles')
