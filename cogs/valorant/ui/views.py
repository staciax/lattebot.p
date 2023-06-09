from __future__ import annotations

import asyncio
import contextlib
import logging

# import abc
import time

# import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import discord

# from async_lru import alru_cache
from discord import ui

import core.utils.chat_formatting as chat
from core.bot import LatteMaid
from core.errors import AppCommandError
from core.i18n import _
from core.ui.views import ViewAuthor
from core.utils.pages import LattePages, ListPageSource

from .. import valorantx2 as valorantx
from ..valorantx2 import RiotAuth
from ..valorantx2.enums import Locale as ValorantLocale, RelationType
from . import embeds as e

if TYPE_CHECKING:
    from core.bot import LatteMaid

    from ..valorantx2 import Client as ValorantClient
    from ..valorantx2.models import RewardValorantAPI
    from .embeds import Embed

__all__ = (
    'AccountManager',
    'CollectionView',
    'FeaturedBundleView',
    'GamePassView',
    'MissionView',
    'NightMarketView',
    'StoreFrontView',
    'WalletView',
)


_log = logging.getLogger(__name__)


class AccountManager:
    def __init__(
        self,
        bot: LatteMaid,
        user_id: int,
        valorant_client: ValorantClient,
        *,
        locale: ValorantLocale = ValorantLocale.american_english,
    ) -> None:
        self._bot: LatteMaid = bot
        self.user_id: int = user_id
        self.locale: ValorantLocale = locale
        self.valorant_client: ValorantClient = valorant_client
        self.first_account: Optional[RiotAuth] = None
        self._riot_accounts: Dict[str, RiotAuth] = {}
        self._hide_display_name: bool = False
        self._ready: asyncio.Event = asyncio.Event()

    async def init(self) -> None:
        assert self.valorant_client.bot is not None
        user = await self._bot.db.get_user(self.user_id)

        if user is None:
            _log.info(f'User {self.user_id!r} not found in database. creating new user.')
            user = await self._bot.db.create_user(id=self.user_id, locale=self.locale.value)

        for index, riot_account in enumerate(sorted(user.riot_accounts, key=lambda x: x.created_at)):
            riot_auth = RiotAuth.from_db(riot_account)
            riot_auth.bot = self._bot
            if time.time() > riot_auth.expires_at:
                with contextlib.suppress(Exception):
                    await riot_auth.reauthorize()
            self._riot_accounts[riot_auth.puuid] = riot_auth
            if index == 0:
                self.first_account = riot_auth
        self._ready.set()

    @property
    def hide_display_name(self) -> bool:
        return self._hide_display_name

    @property
    def riot_accounts(self) -> List[RiotAuth]:
        return list(self._riot_accounts.values())

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    async def fetch_storefront(self, riot_auth: RiotAuth) -> valorantx.StoreFront:
        if sf := self.valorant_client.get_storefront(riot_auth.puuid):
            return sf
        return await self.valorant_client.fetch_storefront(riot_auth)

    def is_ready(self) -> bool:
        return self._ready.is_set()

    def get_riot_account(self, puuid: Optional[str]) -> Optional[RiotAuth]:
        return self._riot_accounts.get(puuid)  # type: ignore

    def set_locale_from_discord(self, locale: discord.Locale) -> None:
        self.locale = valorantx.utils.locale_converter(locale)


class BaseValorantView(ViewAuthor):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        account_manager: AccountManager,
        *,
        check_embeds: bool = True,
    ) -> None:
        super().__init__(interaction)
        self.account_manager: AccountManager = account_manager
        self.check_embeds: bool = check_embeds

    async def interaction_check(self, interaction: discord.Interaction[LatteMaid], /) -> bool:
        if await super().interaction_check(interaction):
            self.account_manager.set_locale_from_discord(interaction.locale)
            return True
        return False

    async def on_timeout(self) -> None:
        if self.message is None:
            try:
                self.message = await self.interaction.original_response()
            except (discord.errors.HTTPException, discord.errors.ClientException, discord.errors.NotFound) as e:
                _log.warning("failed to get original response", exc_info=e)
                return

        self.disable_buttons()
        await self.safe_edit_message(self.message, view=self)

    @staticmethod
    async def safe_edit_message(
        message: discord.Message | discord.InteractionMessage, **kwargs: Any
    ) -> discord.Message | discord.InteractionMessage | None:
        try:
            msg = await message.edit(**kwargs)
        except (discord.errors.HTTPException, discord.errors.Forbidden) as e:
            _log.warning("failed to edit message", exc_info=e)
            return None
        else:
            return msg

    async def send(self, **kwargs: Any) -> None:
        if self.message is None:
            self.message = await self.interaction.followup.send(**kwargs, view=self)
            return
        else:
            await self.safe_edit_message(self.message, **kwargs, view=self)


class ButtonAccountSwitch(ui.Button['BaseSwitchView']):
    def __init__(
        self,
        *,
        label: Optional[str] = None,
        disabled: bool = False,
        custom_id: Optional[str] = None,
        row: Optional[int] = None,
    ) -> None:
        super().__init__(style=discord.ButtonStyle.gray, label=label, disabled=disabled, custom_id=custom_id, row=row)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None

        # enable all buttons without self
        self.disabled = True
        for item in self.view.children:
            if isinstance(item, self.__class__):
                if item.custom_id != self.custom_id:
                    item.disabled = False

        interaction.extras['puuid'] = self.custom_id
        interaction.extras['label'] = self.label

        await self.view.callback(interaction)


class BaseSwitchView(BaseValorantView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager)
        self._ready: asyncio.Event = asyncio.Event()
        self.row: int = 0
        asyncio.create_task(self._initialize())

    async def _initialize(self) -> None:
        await self.account_manager.init()
        self.account_manager.set_locale_from_discord(self.interaction.locale)
        self._build_buttons()
        self._ready.set()

    @property
    def valorant_client(self) -> ValorantClient:
        return self.account_manager.valorant_client

    def _build_buttons(self) -> None:
        for index, acc in enumerate(self.account_manager.riot_accounts, start=1):
            if index >= 4:
                self.row += 1
            self.add_item(
                ButtonAccountSwitch(
                    label="Account #" + str(index) if self.account_manager.hide_display_name else acc.display_name,
                    disabled=(index == 1),
                    custom_id=acc.puuid,
                    row=self.row,
                )
            )

    def remove_switch_button(self) -> None:
        for child in self.children:
            if isinstance(child, ButtonAccountSwitch):
                self.remove_item(child)

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    def get_riot_auth(self, puuid: Optional[str]) -> Optional[RiotAuth]:
        if puuid is not None:
            return self.account_manager.get_riot_account(puuid)
        return self.account_manager.first_account

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        # if self.check_embeds and not interaction.channel.permissions_for(interaction.guild.me).embed_links:  # type: ignore
        #     await interaction.response.send_message(
        #         'Bot does not have embed links permission in this channel.', ephemeral=True
        #     )
        #     return
        if not interaction.response.is_done():
            await interaction.response.defer()
        await self.wait_until_ready()


class StoreFrontView(BaseSwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))

        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get storefront without account')
            return

        storefront = await self.account_manager.fetch_storefront(riot_auth)

        embeds = e.store_e(
            storefront.skins_panel_layout,
            riot_id=riot_auth.display_name,
            locale=self.account_manager.locale,
        )

        await self.send(embeds=embeds)


class NightMarketView(BaseSwitchView):
    def __init__(
        self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager, hide: bool
    ) -> None:
        super().__init__(interaction, account_manager)
        self.row = 1
        self.hide: bool = hide
        self.front_embed: Optional[Embed] = None
        self.prompt_embeds: Optional[List[Embed]] = None
        self.embeds: Optional[List[Embed]] = None
        self.current_opened: Dict[str, int] = {}
        self.current_author_puuid: Optional[str] = None

    @ui.button(label="Open Once", style=discord.ButtonStyle.primary)
    async def open_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        assert self.message is not None
        if self.embeds is None:
            return

        current_opened = 1
        if self.current_author_puuid is not None and self.current_author_puuid in self.current_opened:
            current_opened = self.current_opened[self.current_author_puuid] + 1
        if current_opened > len(self.embeds):
            return
        if self.prompt_embeds is None:
            return

        embeds = []
        embeds.extend(self.embeds[:current_opened])
        embeds.extend(self.prompt_embeds[current_opened:])
        embeds.insert(0, self.front_embed)

        if current_opened == len(self.embeds):
            self.remove_buttons()

        try:
            await self.message.edit(embeds=embeds, view=self)
        except (discord.errors.HTTPException, discord.errors.Forbidden, discord.errors.NotFound):
            pass
        else:
            assert self.current_author_puuid is not None
            assert self.current_author_puuid in self.current_opened
            self.current_opened[self.current_author_puuid] = current_opened

    @ui.button(label="Open All", style=discord.ButtonStyle.primary)
    async def open_all_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        assert self.message is not None
        if self.embeds is None:
            return

        if self.prompt_embeds is None:
            return

        current_opened = len(self.embeds)
        if self.current_author_puuid is not None and self.current_author_puuid in self.current_opened:
            self.current_opened[self.current_author_puuid] = current_opened

        embeds = [self.front_embed, *self.embeds]
        self.remove_buttons()

        try:
            await self.message.edit(embeds=embeds, view=self)
        except (discord.errors.HTTPException, discord.errors.Forbidden, discord.errors.NotFound):
            pass

    def remove_buttons(self) -> None:
        self.remove_item(self.open_button)
        self.remove_item(self.open_all_button)
        self.__button_is_removed = True

    def add_buttons(self) -> None:
        self.add_item(self.open_button)
        self.add_item(self.open_all_button)
        self.__button_is_removed = False

    async def on_timeout(self) -> None:
        # if self.embeds is None:
        #     return
        self.remove_buttons()
        # embeds = [self.front_embed, *self.embeds]
        # await self.safe_edit_message(self.message, embeds=embeds, view=self)
        await super().on_timeout()

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))

        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get storefront without account')
            return

        storefront = await self.account_manager.fetch_storefront(riot_auth)

        if storefront.bonus_store is None:
            raise AppCommandError(f"{chat.bold('Nightmarket')} is not available.")

        self.front_embed = e.nightmarket_front_e(storefront.bonus_store, riot_auth, locale=self.account_manager.locale)
        self.embeds = embeds = [
            e.skin_e(skin, locale=self.account_manager.locale) for skin in storefront.bonus_store.skins
        ]

        if self.hide:
            self.remove_buttons()

            current_opened = 0
            if riot_auth.puuid not in self.current_opened:
                self.current_opened[riot_auth.puuid] = current_opened
            else:
                current_opened = self.current_opened[riot_auth.puuid]
            self.current_author_puuid = riot_auth.puuid

            try:
                self.__button_is_removed
            except AttributeError:
                self.__button_is_removed = False

            if self.__button_is_removed and current_opened < len(self.embeds):
                self.add_buttons()

            self.prompt_embeds = [
                e.skin_e_hide(skin, locale=self.account_manager.locale) for skin in storefront.bonus_store.skins
            ]
            embeds2 = []
            embeds2.extend(self.embeds[:current_opened])
            embeds2.extend(self.prompt_embeds[current_opened:])
            embeds2.insert(0, self.front_embed)
            await self.send(embeds=embeds2)
            return

        await self.send(embeds=embeds)


class WalletView(BaseSwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))

        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get storefront without account')
            return

        wallet = await self.account_manager.valorant_client.fetch_wallet(riot_auth)
        embed = e.wallet_e(wallet, riot_auth.display_name, locale=self.account_manager.locale)
        await self.send(embed=embed)


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
    def __init__(self, interaction: discord.Interaction[LatteMaid], valorant_client: ValorantClient):
        super().__init__(interaction)
        self.valorant_client = valorant_client
        self.selected: bool = False
        self.bundles: Dict[str, valorantx.FeaturedBundle] = {}

    def build_buttons(self, bundles: List[valorantx.FeaturedBundle]) -> None:
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
                locale=valorantx.utils.locale_converter(self.interaction.locale),
            )
            self.message = await self.interaction.followup.send(embeds=embeds, view=self)
        elif len(self.bundles) == 1:
            source = FeaturedBundlePageSource(
                self.bundles[list(self.bundles.keys())[0]], locale=self.interaction.locale
            )
            view = FeaturedBundlePageView(source, interaction=self.interaction)
            await view.start()
        else:
            _log.error(
                f'user {self.interaction.user}({self.interaction.user.id}) tried to get featured bundles without bundles'
            )
            raise AppCommandError('No featured bundles')


class FeaturedBundlePageSource(ListPageSource['Embed']):
    def __init__(self, bundle: valorantx.FeaturedBundle, locale: discord.Locale) -> None:
        self.bundle: valorantx.FeaturedBundle = bundle
        self.locale: discord.Locale = locale
        self.bundle_embed = e.BundleEmbed(bundle, locale=valorantx.utils.locale_converter(locale))
        self.embed: Embed = self.bundle_embed.build_banner_embed()
        super().__init__(self.bundle_embed.build_items_embeds(), per_page=5)

    async def format_page(self, menu: FeaturedBundlePageView, entries: List[Embed]) -> List[Embed]:
        entries.insert(0, self.embed)
        return entries

    def rebuild(self, locale: discord.Locale) -> None:
        _log.debug(f'rebuilding bundle embeds with locale {locale}')
        self.locale = locale
        self.bundle_embed.locale = valorantx.utils.locale_converter(locale)
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
        self.message = await self.interaction.original_response()
        return await super().start()

    # async def start(self, ephemeral: bool = False) -> None:
    #     if self.check_embeds and not self.interaction.channel.permissions_for(self.interaction.guild.me).embed_links:  # type: ignore
    #         await self.interaction.response.send_message(
    #             'Bot does not have embed links permission in this channel.', ephemeral=True
    #         )
    #         return
    #     await self.source._prepare_once()
    #     page = await self.source.get_page(0)
    #     kwargs = await self._get_kwargs_from_page(page)
    #     self._update_labels(0)
    #     # await self.interaction.response.edit_message(**kwargs, view=self)

    #     if self.message is not None:
    #         await self.message.edit(**kwargs, view=self)
    #         return
    #     self.message = await self.interaction.followup.send(**kwargs, view=self, ephemeral=ephemeral)

    # async def on_timeout(self) -> None:
    #     if not self.selected:
    #         original_response = await self.interaction.original_response()
    #         if original_response:
    #             for item in self.children:
    #                 if isinstance(item, ui.Button):
    #                     item.disabled = True
    #             await original_response.edit(view=self)


class GamePassPageSource(ListPageSource['RewardValorantAPI']):
    def __init__(self, contract: valorantx.Contract, riot_auth: RiotAuth, locale: ValorantLocale) -> None:
        self.embed = e.GamePassEmbed(contract, riot_auth, locale=locale)
        super().__init__(contract.content.get_all_rewards(), per_page=1)

    async def format_page(self, menu: GamePassView, page: Any):
        reward = self.entries[menu.current_page]
        return self.embed.build_page_embed(menu.current_page, reward, locale=menu.account_manager.locale)


class GamePassView(BaseSwitchView, LattePages):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        account_manager: AccountManager,
        relation_type: RelationType,
    ) -> None:
        super().__init__(interaction, account_manager)
        self.row = 2
        self.relation_type = relation_type

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))
        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get gamepass without account')
            return

        contracts = await self.account_manager.valorant_client.fetch_contracts(riot_auth)

        contract = (
            contracts.special_contract
            if self.relation_type == RelationType.agent
            else contracts.get_latest_contract(self.relation_type)
        )
        if contract is None:
            raise AppCommandError(f'{chat.bold(self.relation_type.value)} is not available.')

        self.source = GamePassPageSource(contract, riot_auth, locale=self.account_manager.locale)
        self.compact = True
        await self.start(page_number=contract.current_level)


class MissionView(BaseSwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager)
        self.row = 1

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))
        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get gamepass without account')
            return

        contracts = await self.account_manager.valorant_client.fetch_contracts(riot_auth)

        embed = e.mission_e(contracts, riot_auth.display_name, locale=self.account_manager.locale)
        await self.send(embed=embed)


class CollectionView(BaseSwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager)

    # @alru_cache(maxsize=5)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))
        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get gamepass without account')
            return

        collection = await self.valorant_client.fetch_loudout()
        mmr = await self.valorant_client.fetch_mmr()

        embed = e.collection_front_e(collection, mmr, riot_auth.display_name, locale=self.account_manager.locale)
        await self.send(embed=embed)
