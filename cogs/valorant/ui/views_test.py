from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import discord
from discord import ButtonStyle, Locale, SelectOption, ui

from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from core.ui.views import ViewAuthor
from core.utils.pages import LattePages, ListPageSource, PageSource
from valorantx2.enums import RelationType

from ..account_manager import AccountManager
from ..utils import locale_converter
from . import embeds as e

# from .utils import find_match_score_by_player

if TYPE_CHECKING:
    from typing_extensions import Self

    from core.bot import LatteMaid
    from valorantx2.auth import RiotAuth
    from valorantx2.client import Client as ValorantClient
    from valorantx2.models import (  # MatchDetails,; MatchHistory,
        Contract,
        FeaturedBundle,
        Gun,
        GunsLoadout,
        Loadout,
        RewardValorantAPI,
    )


T = TypeVar('T')
V = TypeVar('V', bound='BaseView', covariant=True)

_log = logging.getLogger(__name__)
_ = I18n('valorant.ui.account_management', Path(__file__).resolve().parent, read_only=True)


class ValorantPageSource(PageSource):
    async def format_page_valorant(self, view: Any, page: int, riot_auth: RiotAuth) -> Embed:
        raise NotImplementedError


class ValorantListPageSource(ValorantPageSource, Generic[T]):
    def __init__(self, entries: list[T], per_page: int = 12):
        self.entries = entries
        self.per_page = per_page

        pages, left_over = divmod(len(entries), per_page)
        if left_over:
            pages += 1

        self._max_pages = pages

    def is_paginating(self) -> bool:
        """:class:`bool`: Whether pagination is required."""
        return len(self.entries) > self.per_page

    def get_max_pages(self) -> int:
        """:class:`int`: The maximum number of pages required to paginate this sequence."""
        return self._max_pages

    async def get_page(self, page_number: int) -> Any | list[Any]:
        """Returns either a single element of the sequence or
        a slice of the sequence.
        If :attr:`per_page` is set to ``1`` then this returns a single
        element. Otherwise it returns at most :attr:`per_page` elements.
        Returns
        ---------
        Union[Any, List[Any]]
            The data returned.
        """
        if self.per_page == 1:
            return self.entries[page_number]
        else:
            base = page_number * self.per_page
            return self.entries[base : base + self.per_page]


class AccountSelect(ui.Select[V]):
    def __init__(
        self,
        *,
        options: list[SelectOption],
        row: int | None = None,
        locale: Locale | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            placeholder=_('select.account', locale),
            options=options or [SelectOption(label=_('account_select_no_account'), value='no_account')],
            row=row,
            **kwargs,
        )
        if len(options) <= 1:
            self.disabled = True

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        value = interaction.extras['puuid'] = self.values[0]

        await interaction.response.defer()

        if value == 'no_account':
            return

        if self.view.current_puuid == value:
            return

        await self.view.switch_account_to(value)

    # self.current_puuid = value

    @classmethod
    def from_account_manager(
        cls,
        account_manager: AccountManager,
        locale: Locale | None = None,
    ) -> Self:
        options = [
            SelectOption(label=account.display_name or account.riot_id, value=account.puuid)
            for account in account_manager.accounts
        ]
        if account_manager.author.locale is not None:
            locale = discord.Locale(account_manager.author.locale)

        return cls(options=options, locale=locale)


class BaseView(ViewAuthor):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        source: ValorantPageSource = discord.utils.MISSING,
    ) -> None:
        super().__init__(interaction)
        self.source: ValorantPageSource = source
        self.current_puuid: str | None = None
        self.account_manager: AccountManager | None = None

    @property
    def valorant_client(self) -> ValorantClient:
        return self.bot.valorant_client

    def _fill_account_select(self) -> None:
        if self.account_manager is None:
            return

        if not len(self.account_manager.accounts):
            return

        self.add_item(AccountSelect.from_account_manager(account_manager=self.account_manager, locale=self.locale))

    # async def show_page_valorant(self, interaction: discord.Interaction[LatteMaid], page_number: int) -> None:
    #     page = await self.source.get_page(page_number)
    #     self.current_page = page_number
    #     kwargs = await self._get_kwargs_from_valorant_page(page)
    #     # self._update_labels(page_number)
    #     if kwargs:
    #         if interaction.response.is_done():
    #             if self.message:
    #                 await self.message.edit(**kwargs, view=self)
    #         else:
    #             await interaction.response.edit_message(**kwargs, view=self)

    async def _get_kwargs_from_valorant_page(self, page: int) -> dict[str, Any]:
        if self.account_manager is None:
            return {}
        riot_auth = self.account_manager.get_account(self.current_puuid)  # type: ignore
        if riot_auth is None:
            return {}
        value = await self.source.format_page_valorant(self, page, riot_auth)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {'content': value, 'embed': None}
        elif isinstance(value, discord.Embed):
            return {'embed': value, 'content': None}
        elif isinstance(value, list) and all(isinstance(v, discord.Embed) for v in value):  # type: ignore
            return {'embeds': value, 'content': None}
        else:
            return {}

    async def _init(self) -> None:
        user = await self.bot.db.fetch_user(self.author.id)
        if user is None:
            return
        self.account_manager = AccountManager(user, bot=self.bot, re_authorize=False)
        await self.account_manager.wait_until_ready()
        if not self.account_manager.accounts:
            raise ValueError('No accounts found')
        # if self.account_manager.main_account is None:
        #     raise ValueError('No main account found')
        assert self.account_manager.main_account is not None
        self.current_puuid = self.account_manager.main_account.puuid
        self._fill_account_select()

    async def switch_account_to(self, puuid: str, /) -> None:
        self.current_puuid = puuid
        page = getattr(self, 'current_page', 0)
        kwargs = await self._get_kwargs_from_valorant_page(page)
        if self.message is not None:
            await self.message.edit(**kwargs, view=self)

    async def start_valorant(self) -> None:
        await self.interaction.response.defer()
        await self._init()
        kwargs = await self._get_kwargs_from_valorant_page(0)
        if not kwargs:
            kwargs = {'content': _('no_data', self.locale)}
        self.message = await self.interaction.followup.send(**kwargs, view=self)


# bundles


class FeaturedBundlePageSource(ListPageSource['Embed']):
    def __init__(self, bundle: FeaturedBundle, locale: discord.Locale) -> None:
        self.bundle: FeaturedBundle = bundle
        self.locale: discord.Locale = locale
        self.bundle_embed = e.BundleEmbed(bundle, locale=self.locale)
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
    def __init__(self, interaction: discord.Interaction[LatteMaid], valorant_client: ValorantClient) -> None:
        super().__init__(interaction)
        self.valorant_client = valorant_client  # interaction.client.valorant_client
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
        bundles = await self.valorant_client.fetch_featured_bundle()
        self.bundles = {bundle.uuid: bundle for bundle in bundles if bundle is not None}

        if len(self.bundles) > 1:
            self.build_buttons(list(self.bundles.values()))
            embeds = e.select_featured_bundles_e(
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


# game pass


class GamePassPageSource(ListPageSource['RewardValorantAPI']):
    def __init__(self, contract: Contract, riot_id: str, locale: discord.Locale) -> None:
        self.embed = e.GamePassEmbed(contract, riot_id, locale=locale)
        super().__init__(contract.content.get_all_rewards(), per_page=1)

    async def format_page(self, menu: GamePassView, page: Any):
        reward = self.entries[menu.current_page]
        return self.embed.build_page_embed(menu.current_page, reward, locale=menu.locale)


class GamePassView(BaseView, LattePages):
    source: GamePassPageSource

    def __init__(self, interaction: discord.Interaction[LatteMaid], relation_type: RelationType) -> None:
        super().__init__(interaction=interaction)
        self.compact = True
        self.relation_type = relation_type

    async def switch_account_to(self, puuid: str, /) -> None:
        await self.set_source(puuid)
        await super().switch_account_to(puuid)

    async def set_source(self, puuid: str | None, /) -> None:
        assert self.account_manager is not None
        assert self.current_puuid is not None
        riot_auth = self.account_manager.get_account(puuid)  # type: ignore
        assert riot_auth is not None
        contracts = await self.valorant_client.fetch_contracts(riot_auth)
        contract = (
            contracts.special_contract
            if self.relation_type == RelationType.agent
            else contracts.get_latest_contract(self.relation_type)
        )
        if contract is None:
            raise ValueError('No contract found')
        self.source = GamePassPageSource(contract, riot_auth.riot_id, locale=self.locale)
        self.current_page = contract.current_level

    async def start_valorant(self) -> None:
        await self._init()
        await self.set_source(self.current_puuid)
        await self.start(self.current_page)


# storefront


class StoreFrontView(BaseView):
    def __init__(
        self, interaction: discord.Interaction[LatteMaid], source: ValorantPageSource = discord.utils.MISSING
    ) -> None:
        super().__init__(interaction, source)
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


# collection


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
        self.embed = e.collection_front_e(
            self.loadout,
            # mmr,
            riot_auth.riot_id,
            locale=locale_converter.to_valorant(view.locale),
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
        return [e.skin_loadout_e(skin, locale=locale_converter.to_valorant(view.locale)) for skin in entries]


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
            embed = e.spray_loadout_e(spray, slot, locale=locale_converter.to_valorant(interaction.locale))

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


# carrirer
