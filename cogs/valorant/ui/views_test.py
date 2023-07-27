from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import discord
from discord import ui
from discord.components import SelectOption
from discord.enums import ButtonStyle, Locale

from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from core.ui.views import ViewAuthor
from core.utils.pages import LattePages, ListPageSource, PageSource
from valorantx2.enums import RelationType
from valorantx2.utils import locale_converter

from ..account_manager import AccountManager
from . import embeds as e
from .utils import find_match_score_by_player

if TYPE_CHECKING:
    from typing_extensions import Self

    from core.bot import LatteMaid
    from valorantx2.auth import RiotAuth
    from valorantx2.client import Client as ValorantClient
    from valorantx2.models import Contract, FeaturedBundle, MatchDetails, MatchHistory, RewardValorantAPI


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
            placeholder=_('account_select_placeholder', locale),
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
        row: int = 0,
        locale: Locale | None = None,
    ) -> Self:
        options = [
            SelectOption(label=account.display_name or account.riot_id, value=account.puuid)
            for account in account_manager.accounts
        ]
        if account_manager.author.locale is not None:
            locale = discord.Locale(account_manager.author.locale)

        return cls(options=options, row=row, locale=locale)


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

        # move all children down by 1
        for item in self.children:
            if item.row is None:
                continue
            item.row += 1

        self.add_item(
            AccountSelect.from_account_manager(
                account_manager=self.account_manager,
                locale=self.locale,
            )
        )

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
        kwargs = await self._get_kwargs_from_valorant_page(0)
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
        self.current_puuid = puuid
        await self.set_source()
        kwargs = await self._get_kwargs_from_page(self.current_page)
        if self.message is not None:
            await self.message.edit(**kwargs, view=self)

    async def set_source(self) -> None:
        assert self.account_manager is not None
        assert self.current_puuid is not None
        riot_auth = self.account_manager.get_account(self.current_puuid)
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
        await self.set_source()
        await self.start(self.current_page)


# carrirer


# class SelectMatchHistory(ui.Select['CarrierView']):
#     def __init__(self, *, options: list[discord.SelectOption], locale: discord.Locale) -> None:
#         super().__init__(
#             options=options or [discord.SelectOption(label=_('No Match History', locale), value='0')],
#             placeholder=_('Select Match to see details', locale),
#             row=1,
#             disabled=not options,
#         )
#         self.locale = locale

#     @classmethod
#     def from_match_history(
#         cls,
#         *,
#         match_history: MatchHistory,
#         locale: discord.Locale,
#     ) -> Self:
#         options = []
#         for match in match_history.match_details:
#             me = match.get_player(match_history.subject)
#             if me is None:
#                 continue

#             # find match score
#             left_team_score, right_team_score = find_match_score_by_player(match, me)  # type: ignore

#             # build option
#             option = discord.SelectOption(
#                 label=f'{left_team_score} - {right_team_score}',
#                 value=match.match_info.match_id,
#             )

#             # add emoji
#             if me.agent is not None:
#                 option.emoji = getattr(me.agent, 'emoji', None)

#             # add description
#             game_mode = match.match_info.game_mode
#             match_map = match.match_info.map
#             if match_map is not None and game_mode is not None:
#                 option.description = '{map} - {gamemode}'.format(
#                     map=match_map.display_name.from_locale(locale_converter.to_valorant(locale)),
#                     gamemode=game_mode.display_name.from_locale(locale_converter.to_valorant(locale)),
#                 )
#             options.append(option)
#         return cls(options=options, locale=discord.Locale.american_english)

#     def clear(self) -> None:
#         self.options.clear()

#     def add_dummy(self) -> None:
#         assert self.view is not None
#         self.clear()
#         self.add_option(label=_('No Match History', self.view.locale), value='0', emoji='📭')
#         self.disabled = True

#     async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
#         assert self.view is not None
#         # async with self.view.lock:
#         #     value = self.values[0]

#         #     await interaction.response.defer()

#         #     if self.puuid == '':
#         #         return

#         #     if value not in self._source:
#         #         return

#         #     # build source
#         #     source = MatchDetailsPageSource(self._source[value], self.puuid, locale_converter.to_valorant(self.view.locale))
#         #     self.match_details_view.source = source

#         #     # set message
#         #     if self.match_details_view.message is None and self.view.message is not None:
#         #         self.match_details_view.message = self.view.message

#         #     # start view
#         #     await self.match_details_view.start()


# class CarrierView(BaseView, LattePages):
#     def __init__(
#         self,
#         interaction: discord.Interaction[LatteMaid],
#         queue_id: str | None = None,
#     ) -> None:
#         super().__init__(interaction=interaction)
#         self.queue_id: str | None = queue_id
#         self.embeds: list[Embed] = []

#     def fill_items(self) -> None:
#         super().fill_items()
#         self.remove_item(self.stop_pages)
#         self.remove_item(self.numbered_page)

#     async def set_source(self) -> None:
#         assert self.account_manager is not None
#         assert self.current_puuid is not None
#         match_history = await self.valorant_client.fetch_match_history(
#             puuid=self.current_puuid,
#             queue=self.queue_id,
#             with_details=True,
#         )
#         self.add_item(
#             SelectMatchHistory.from_match_history(match_history=match_history, locale=self.locale),
#         )
#         self.source = CarrierPageSource(puuid=riot_auth.puuid, data=match_history.match_details)  # type: ignore

#     async def start_valorant(self) -> None:
#         await self.interaction.response.defer()
#         await self._init()
#         await self.set_source()
#         await self.start()


# class MatchDetailsPageSource(ListPageSource):
#     def __init__(self, match_details: MatchDetails, puuid: str, locale: discord.Locale) -> None:
#         self.puuid = puuid
#         self.locale = locale
#         self.match_embed = e.MatchDetailsEmbed(match_details)  # type: ignore
#         super().__init__(self.build_entries(locale), per_page=1)

#     def build_entries(self, locale: discord.Locale) -> list[tuple[Embed, Embed]]:
#         entries = []
#         try:
#             desktops, mobiles = self.match_embed.build(self.puuid, locale=locale_converter.to_valorant(locale))
#         except Exception as exc:
#             _log.error(f'failed to build match details embed for {self.puuid}', exc_info=exc)
#         else:
#             for dt, mb in zip(desktops, mobiles):
#                 entries.append((dt, mb))
#         return entries

#     def format_page(self, menu: MatchDetailsView, entries: tuple[Embed, Embed]) -> Embed:
#         desktops, mobiles = entries

#         # locale changed
#         if menu.locale != self.locale:
#             self.locale = menu.locale
#             self.entries = self.build_entries(self.locale)
#             desktops, mobiles = self.entries[menu.current_page]

#         return mobiles if menu.is_on_mobile() else desktops


# class MatchDetailsView(ViewAuthor, LattePages):
#     __view_on_mobile__: bool = False

#     def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
#         super().__init__(interaction)
#         self.compact = True
#         # self.source = source
#         # self.carrier_view: Optional[CarrierView] = carrier_view
#         # self.valorant_locale: ValorantLocale = locale_converter.to_valorant(interaction.locale)
#         # self.back_to_home.label = _('Back', self.locale)

#     def fill_items(self) -> None:
#         # if self.carrier_view is not None:
#         #     self.add_item(self.back_to_home)
#         super().fill_items()
#         self.remove_item(self.go_to_last_page)
#         self.remove_item(self.go_to_first_page)
#         self.remove_item(self.stop_pages)
#         self.go_to_next_page.label = self.go_to_last_page.label
#         self.go_to_previous_page.label = self.go_to_first_page.label
#         # self.add_item(self.toggle_ui)

#     def is_on_mobile(self) -> bool:
#         return self.__view_on_mobile__

#     # @ui.button(emoji='📱', style=ButtonStyle.green)
#     # async def toggle_ui(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
#     #     button.emoji = '📱' if self.is_on_mobile() else '💻'
#     #     self.__view_on_mobile__ = not self.is_on_mobile()
#     #     await self.show_checked_page(interaction, self.current_page)

#     # @ui.button(label=_('Back'), style=ButtonStyle.gray, custom_id='home_button')
#     # async def back_to_home(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
#     #     # assert self.carrier_view is not None
#     #     await interaction.response.defer()

#     #     if self.carrier_view is None:
#     #         return

#     #     if self.message is None:
#     #         return

#     #     self.carrier_view.reset_timeout()

#     #     await self.safe_edit_message(self.message, embeds=self.carrier_view.embeds, view=self.carrier_view)
