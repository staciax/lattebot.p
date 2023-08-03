from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord import ButtonStyle, ui

import core.utils.chat_formatting as chat
from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from core.utils.pages import ListPageSource
from valorantx2.models import SkinChroma

from ..utils import locale_converter
from .base import BaseView, ValorantPageSource

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2.auth import RiotAuth
    from valorantx2.models import Gun, GunsLoadout, Loadout, Spray


_ = I18n('valorant.features.loadout', Path(__file__).resolve().parent, read_only=True)


def collection_front_e(
    loadout: Loadout,
    # mmr: MatchmakingRating,
    riot_id: str,
    *,
    locale: discord.Locale = discord.Locale.american_english,
) -> Embed:
    # latest_tier = mmr.get_latest_rank_tier() if mmr is not None else None

    vlocale = locale_converter.to_valorant(locale)

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
        embed.title = loadout.identity.player_title.text.from_locale(vlocale)

    if loadout.identity.player_card is not None:
        embed.set_image(url=loadout.identity.player_card.wide_art)
        # card_color_thief = await self.bot.get_or_fetch_colors(
        #     loadout.identity.player_card.uuid, loadout.identity.player_card.wide_art
        # )
        # embed.colour = random.choice(card_color_thief)

    return embed


def skin_loadout_e(gun: Gun, *, locale: discord.Locale = discord.Locale.american_english) -> Embed:
    assert gun.skin_loadout is not None

    vlocale = locale_converter.to_valorant(locale)
    skin_name: str = gun.skin_loadout.display_name.from_locale(vlocale)
    if isinstance(gun.skin_loadout, SkinChroma) and gun.skin_loadout.parent is not None:
        skin_name = gun.skin_loadout.parent.display_name.from_locale(vlocale)

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
        buddy_name = gun.buddy_loadout.display_name.from_locale(vlocale)
        embed.set_footer(
            text=f'{buddy_name}' + (' ★' if gun.buddy_loadout.is_favorite() else ''),
            icon_url=gun.buddy_loadout.display_icon,
        )
    return embed


def spray_loadout_e(
    spray: Spray,
    slot: int,
    *,
    locale: discord.Locale = discord.Locale.american_english,
) -> Embed:
    vlocale = locale_converter.to_valorant(locale)
    spray_name = spray.display_name.from_locale(vlocale)
    embed = Embed(description=chat.bold(str(slot) + '. ' + spray_name.strip()) + (' ★' if spray.is_favorite() else ''))
    spray_icon = spray.animation_gif or spray.full_transparent_icon or spray.display_icon
    if spray_icon is not None:
        embed.set_thumbnail(url=spray_icon)
    return embed


class CollectionFrontPageSource(ValorantPageSource):
    def __init__(self) -> None:
        super().__init__()
        self.loadout: Loadout | None = None
        self.skin_source: SkinCollectionSource | None = None
        self.embed: Embed | None = None

    async def format_page_valorant(self, view: BaseView, page: int, riot_auth: RiotAuth) -> Embed:
        self.loadout = await view.valorant_client.fetch_loudout(riot_auth)
        if self.loadout.guns is not None:
            self.skin_source = SkinCollectionSource(self.loadout.guns)
        self.embed = collection_front_e(
            self.loadout,
            # mmr,
            riot_auth.riot_id,
            locale=view.locale,
        )
        return self.embed


class SkinCollectionSource(ListPageSource):
    def __init__(self, gun_loadout: GunsLoadout):
        def gun_priority(gun: Gun) -> int:
            # page 1
            name = gun.display_name.default.lower()

            if name == 'phantom':
                return 0
            elif name == 'vandal':
                return 1
            elif name == 'operator':
                return 2
            elif gun.is_melee():
                return 3

            # page 2
            elif name == 'classic':
                return 4
            elif name == 'sheriff':
                return 5
            elif name == 'spectre':
                return 6
            elif name == 'marshal':
                return 7

            # page 3
            elif name == 'stinger':
                return 8
            elif name == 'bucky':
                return 9
            elif name == 'guardian':
                return 10
            elif name == 'ares':
                return 11

            # page 4
            elif name == 'shorty':
                return 12
            elif name == 'frenzy':
                return 13
            elif name == 'ghost':
                return 14
            elif name == 'judge':
                return 15

            # page 5
            elif name == 'bulldog':
                return 16
            elif name == 'odin':
                return 17
            else:
                return 18

        super().__init__(sorted(list(gun_loadout.to_list()), key=gun_priority), per_page=4)
        self.current_page: int = 0

    async def format_page(
        self,
        view: CollectionView,
        entries: list[Gun],
    ) -> list[Embed]:
        return [skin_loadout_e(skin, locale=view.locale) for skin in entries]


class CollectionView(BaseView):
    def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__(interaction)
        self.source: CollectionFrontPageSource = CollectionFrontPageSource()
        self.skin_prev_button = CollectionSkinPrevButton()
        self.skin_next_button = CollectionSkinNextButton()

    def _fill_components(self) -> None:
        self.add_items(
            CollectionSkinsButton(label=_('button.collection.skins', self.locale)),
            CollectionSpraysButton(label=_('button.collection.sprays', self.locale)),
        )

    async def _init(self) -> None:
        self._fill_components()
        await super()._init()

    # skin pages

    async def show_skin_checked_page(self, interaction: discord.Interaction[LatteMaid], page_number: int) -> None:
        if self.source.skin_source is None:
            return
        max_pages = self.source.skin_source.get_max_pages()
        try:
            if max_pages > page_number >= 0:
                await self.show_skin_page(interaction, page_number)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def show_skin_page(self, interaction: discord.Interaction[LatteMaid], page_number: int) -> None:
        assert self.source.skin_source is not None
        source = self.source.skin_source
        page = await source.get_page(page_number)
        source.current_page = page_number
        embeds = await source.format_page(self, page)

        # update buttons
        self.skin_prev_button.disabled = page_number == 0
        self.skin_next_button.disabled = page_number == 4

        if interaction.response.is_done():
            if self.message:
                await self.message.edit(embeds=embeds, view=self)
        else:
            await interaction.response.edit_message(embeds=embeds, view=self)


class CollectionSkinsButton(ui.Button['CollectionView']):
    def __init__(
        self,
        *,
        style: ButtonStyle = ButtonStyle.primary,
        label: str | None = None,
        disabled: bool = False,
        custom_id: str | None = None,
        # emoji: str | Emoji | PartialEmoji | None = None,
    ):
        super().__init__(
            style=style, label=label, disabled=disabled, custom_id=custom_id, emoji='<:discordsagegun:1104332724631765043>'
        )

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> Any:
        assert self.view is not None
        assert self.view.message is not None
        assert self.view.source.loadout is not None
        assert self.view.source.skin_source is not None

        await interaction.response.defer()
        if self.view.source.loadout.guns is None:
            return

        self.view.clear_items()
        self.view.add_items(
            self.view.skin_prev_button,
            self.view.skin_next_button,
            CollectionBackToFrontButton(row=1),
        )

        await self.view.show_skin_page(interaction, 0)


class CollectionSkinNextButton(ui.Button['CollectionView']):
    def __init__(
        self,
        *,
        style: ButtonStyle = ButtonStyle.primary,
        disabled: bool = False,
        custom_id: str | None = None,
        url: str | None = None,
        # emoji: str | Emoji | PartialEmoji | None = None,
        row: int | None = None,
    ):
        super().__init__(style=style, label='≫', disabled=disabled, custom_id=custom_id, url=url, row=row)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> Any:
        assert self.view is not None
        assert self.view.message is not None
        assert self.view.source.skin_source is not None

        await interaction.response.defer()

        await self.view.show_skin_page(interaction, self.view.source.skin_source.current_page + 1)


class CollectionSkinPrevButton(ui.Button['CollectionView']):
    def __init__(
        self,
        *,
        style: ButtonStyle = ButtonStyle.primary,
        disabled: bool = False,
        custom_id: str | None = None,
        url: str | None = None,
        # emoji: str | Emoji | PartialEmoji | None = None,
        row: int | None = None,
    ):
        super().__init__(style=style, label='≪', disabled=disabled, custom_id=custom_id, url=url, row=row)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> Any:
        assert self.view is not None
        assert self.view.message is not None
        assert self.view.source.skin_source is not None

        await interaction.response.defer()

        await self.view.show_skin_page(interaction, self.view.source.skin_source.current_page - 1)


class CollectionSpraysButton(ui.Button['CollectionView']):
    def __init__(
        self,
        *,
        style: ButtonStyle = ButtonStyle.primary,
        label: str | None = None,
        disabled: bool = False,
        custom_id: str | None = None,
        # emoji: str | Emoji | PartialEmoji | None = None,
    ):
        super().__init__(
            style=style,
            label=label,
            disabled=disabled,
            custom_id=custom_id,
            emoji='<:spray:971941939190595667>',
        )

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> Any:
        assert self.view is not None
        assert self.view.message is not None
        assert self.view.source.loadout is not None

        await interaction.response.defer()
        sprays = self.view.source.loadout.sprays
        if sprays is None:
            return

        self.view.clear_items()
        self.view.add_item(CollectionBackToFrontButton())

        embeds = []
        for slot, spray in enumerate(sprays.to_list(), start=1):
            if spray is None:
                continue
            embed = spray_loadout_e(spray, slot, locale=interaction.locale)

            # if embed._thumbnail.get('url'):
            #     color_thief = await self.bot.get_or_fetch_colors(spray.uuid, embed._thumbnail['url'])
            #     embed.colour = random.choice(color_thief)

            embeds.append(embed)

        await self.view.message.edit(embeds=embeds, view=self.view)


class CollectionBackToFrontButton(ui.Button['CollectionView']):
    def __init__(
        self,
        *,
        disabled: bool = False,
        custom_id: str | None = None,
        # emoji: str | Emoji | PartialEmoji | None = None,
        row: int | None = None,
    ):
        super().__init__(label='<', style=ButtonStyle.secondary, disabled=disabled, custom_id=custom_id, row=row)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> Any:
        assert self.view is not None
        assert self.view.message is not None
        assert self.view.source.embed is not None

        await interaction.response.defer()
        self.view.clear_items()
        self.view._fill_components()
        self.view._fill_account_select()

        await self.view.message.edit(embed=self.view.source.embed, view=self.view)
