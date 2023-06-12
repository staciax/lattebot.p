from __future__ import annotations

import asyncio
import contextlib
import logging

# import abc
import time

# import random
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union

import discord
from async_lru import alru_cache
from discord import ButtonStyle, Interaction, ui
from discord.emoji import Emoji
from discord.partial_emoji import PartialEmoji
from discord.utils import MISSING

import core.utils.chat_formatting as chat
import valorantx2 as valorantx
from core.bot import LatteMaid
from core.errors import AppCommandError
from core.i18n import _
from core.ui.views import BaseView, ViewAuthor
from core.utils.pages import LattePages, ListPageSource
from core.utils.useful import MiadEmbed as Embed
from valorantx2 import RiotAuth
from valorantx2.enums import Locale as ValorantLocale, RelationType

from . import embeds as e, utils

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2 import Client as ValorantClient
    from valorantx2.models import RewardValorantAPI
    from valorantx2.models.custom.match import MatchDetails


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

ViewT = TypeVar('ViewT', bound='BaseView')

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

        async with self.view.lock:
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
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        account_manager: AccountManager,
        row: int = 0,
    ) -> None:
        super().__init__(interaction, account_manager)
        self._ready: asyncio.Event = asyncio.Event()
        self.row: int = row
        self.lock: asyncio.Lock = asyncio.Lock()
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
        super().__init__(interaction, account_manager, row=1)
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

        wallet = await self.valorant_client.fetch_wallet(riot_auth)
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
        super().__init__(interaction, account_manager, row=2)
        self.relation_type = relation_type

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))
        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get gamepass without account')
            return

        contracts = await self.valorant_client.fetch_contracts(riot_auth)

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
        # self.row = 1

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))
        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get gamepass without account')
            return

        contracts = await self.valorant_client.fetch_contracts(riot_auth)

        embed = e.mission_e(contracts, riot_auth.display_name, locale=self.account_manager.locale)
        await self.send(embed=embed)


# collection


class SkinCollectionSourceX(ListPageSource):
    def __init__(self, gun_loadout: valorantx.GunsLoadout):
        def gun_priority(gun: valorantx.Gun) -> int:
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

    async def format_page(
        self,
        view: SkinCollectionViewX,
        entries: List[valorantx.Gun],
    ) -> List[discord.Embed]:
        return [e.skin_loadout_e(skin, locale=view.collection_view.account_manager.locale) for skin in entries]


class SkinCollectionViewX(ViewAuthor, LattePages):
    def __init__(
        self,
        # interaction: discord.Interaction[LatteMaid],
        collection_view: CollectionView,
    ) -> None:
        super().__init__(collection_view.interaction, timeout=600.0)
        self.collection_view = collection_view
        self.compact = True

    def fill_items(self) -> None:
        super().fill_items()
        self.remove_item(self.stop_pages)
        self.add_item(self.back)

    @ui.button(label=_('Back'), style=discord.ButtonStyle.green, custom_id='back', row=1)
    async def back(self, interaction: discord.Interaction[LatteMaid], button: ui.Button):
        self.collection_view.reset_timeout()
        await interaction.response.defer()
        if self.collection_view.message is None:
            return
        if self.collection_view.embed is None:
            return
        await self.collection_view.message.edit(embed=self.collection_view.embed, view=self.collection_view)

    # @ui.button(label=_('Change Skin'), style=discord.ButtonStyle.grey, custom_id='change_skin', row=1, disabled=True)
    # async def change_skin(self, interaction: discord.Interaction[LatteMaid], button: ui.Button):
    #     pass

    async def start_view(self) -> None:
        loadout = self.collection_view.loadout
        if loadout is None:
            return
        self.source = SkinCollectionSourceX(loadout.guns)
        self.message = self.collection_view.message
        await self.start()


class SprayCollectionView(ViewAuthor):
    def __init__(
        self,
        # interaction: discord.Interaction[LatteMaid],
        collection_view: CollectionView,
    ) -> None:
        super().__init__(collection_view.interaction, timeout=600)
        self.collection_view = collection_view
        self.embeds: List[Embed] = []

    # @alru_cache(maxsize=5)
    async def build_embeds(self, spray_loadout: valorantx.SpraysLoadout) -> List[Embed]:
        embeds = []
        for slot, spray in enumerate(spray_loadout.to_list(), start=1):
            if spray is None:
                continue
            embed = e.spray_loadout_e(spray, slot, locale=self.collection_view.account_manager.locale)

            # if embed._thumbnail.get('url'):
            #     color_thief = await self.bot.get_or_fetch_colors(spray.uuid, embed._thumbnail['url'])
            #     embed.colour = random.choice(color_thief)

            embeds.append(embed)
        return embeds

    @ui.button(label=_('Back'), style=ButtonStyle.green, custom_id='back', row=0)
    async def back(self, interaction: discord.Interaction[LatteMaid], button: ui.Button):
        self.collection_view.reset_timeout()
        await interaction.response.defer()
        if self.collection_view.message is None:
            return
        if self.collection_view.embed is None:
            return
        await self.collection_view.message.edit(embed=self.collection_view.embed, view=self.collection_view)

    # @ui.button(label=_('Change Spray'), style=discord.ButtonStyle.grey, custom_id='change_spray', row=0, disabled=True)
    # async def change_spray(self, interaction: dffiscord.Interaction[LatteMaid], button: ui.Button):
    #     pass

    async def start_view(self) -> None:
        if self.collection_view.message is None:
            return
        if self.collection_view.loadout is None:
            return
        self.embeds = await self.build_embeds(self.collection_view.loadout.sprays)
        await self.collection_view.message.edit(embeds=self.embeds, view=self)


class CollectionView(BaseSwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager, row=1)
        self.loadout: Optional[valorantx.Loadout] = None
        self.mmr: Optional[valorantx.MatchmakingRating] = None
        self.embed: Optional[Embed] = None
        # other views
        self.skin_view = SkinCollectionViewX(self)
        self.spray_view = SprayCollectionView(self)

    @alru_cache(maxsize=5)
    async def fetch_loudout(self, riot_auth: RiotAuth) -> valorantx.Loadout:
        loadout = await self.valorant_client.fetch_loudout(riot_auth)
        return loadout

    # @alru_cache(maxsize=5)
    # async def fetch_mmr(self, riot_auth: RiotAuth) -> valorantx.MatchmakingRating:
    #     mmr = await self.valorant_client.fetch_mmr(riot_auth=riot_auth)
    #     return mmr

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))
        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get gamepass without account')
            return

        self.loadout = loadout = await self.fetch_loudout(riot_auth)
        # self.mmr = mmr = await self.fetch_mmr(riot_auth)

        self.embed = embed = e.collection_front_e(
            loadout,
            # mmr,
            riot_auth.display_name,
            locale=self.account_manager.locale,
        )
        await self.send(embed=embed)

    async def on_timeout(self) -> None:
        await self.fetch_loudout.cache_close()
        # await self.fetch_mmr.cache_close()
        return await super().on_timeout()

    @ui.button(label=_('Skin'), style=ButtonStyle.blurple)
    async def skin(self, interaction: discord.Interaction[LatteMaid], button: ui.Button):
        await interaction.response.defer()
        await self.skin_view.start_view()

    @ui.button(label=_('Spray'), style=ButtonStyle.blurple)
    async def spray(self, interaction: discord.Interaction[LatteMaid], button: ui.Button):
        await interaction.response.defer()
        await self.spray_view.start_view()


# match history


class SelectOptionMatchHistory(discord.SelectOption):
    def __init__(
        self,
        *,
        label: str,
        value: str = MISSING,
        description: Optional[str] = None,
        emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
        default: bool = False,
        match_id: str,
    ) -> None:
        super().__init__(label=label, value=value, description=description, emoji=emoji, default=default)
        self.match_id: str = match_id


class SelectMatchHistory(ui.Select['CarrierView']):
    def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__(placeholder=_("Select Match to see details"), max_values=1, min_values=1, row=1)
        self._source: Dict[str, MatchDetails] = {}
        self.puuid: str = ''
        self.match_details_view = MatchDetailsView(interaction, self.view)

    def build_selects(
        self,
        match_details: List[MatchDetails],
        puuid: str,
        locale: ValorantLocale,
    ) -> None:
        self._source = {match.match_info.match_id: match for match in match_details}
        self.puuid = puuid
        for match in match_details:
            me = match.get_player(puuid)
            if me is None:
                continue

            # find match score
            left_team_score, right_team_score = utils.find_match_score_by_player(match, me)

            # build option
            option = discord.SelectOption(
                label=f'{left_team_score} - {right_team_score}',
                value=match.match_info.match_id,
            )

            # add emoji
            if me.agent is not None:
                option.emoji = getattr(me.agent, 'emoji', None)

            # add description
            game_mode = match.match_info.game_mode
            match_map = match.match_info.map
            if match_map is not None and game_mode is not None:
                option.description = (
                    f'{match_map.display_name.from_locale(locale)} - {game_mode.display_name.from_locale(locale)}'
                )

            self.append_option(option)

    def clear(self) -> None:
        self.options.clear()

    def add_dummy(self) -> None:
        self.clear()
        self.add_option(label=_('No Match History'), value='0', emoji='📭')
        self.disabled = True

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        async with self.view.lock:
            value = self.values[0]

            await interaction.response.defer()

            if self.puuid == '':
                return

            if value not in self._source:
                return

            # build source
            source = MatchDetailsPageSource(self._source[value], self.puuid)
            self.match_details_view.source = source

            # set message
            if self.match_details_view.message is None and self.view.message is not None:
                self.match_details_view.message = self.view.message

            # start view
            await self.match_details_view.start()


class CarrierPageSource(ListPageSource):
    def __init__(self, puuid: str, data: List[MatchDetails], per_page: int = 3):
        super().__init__(data, per_page=per_page)
        self.puuid = puuid

    def format_page(self, menu: CarrierView, entries: List[MatchDetails]) -> Union[List[Embed], Embed]:
        embeds = []

        for child in reversed(menu.children):
            # find select menu
            if not isinstance(child, SelectMatchHistory):
                continue

            # no match history
            if len(entries) == 0:
                child.add_dummy()
                return Embed(description=_('No Match History')).warning()
            # build pages
            for match in entries:
                embeds.append(e.match_history_select_e(match, self.puuid, locale=menu.account_manager.locale))

            # build select menu
            child.clear()
            child.disabled = False
            child.build_selects(entries, self.puuid, menu.account_manager.locale)
            break

        return embeds


class CarrierView(BaseSwitchView, LattePages):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        account_manager: AccountManager,
        queue_id: Optional[str] = None,
    ) -> None:
        super().__init__(interaction, account_manager, 2)
        self.queue_id: Optional[str] = queue_id

    def fill_items(self) -> None:
        super().fill_items()
        self.remove_item(self.stop_pages)
        self.remove_item(self.numbered_page)
        self.add_item(SelectMatchHistory(self.interaction))

    # def __init__(self, interaction: Interaction, v_user: ValorantUser, client: ValorantClient) -> None:
    #     super().__init__(interaction, v_user, client, row=2)
    #     # self.mmr: Optional[valorantx.MMR] = None
    #     self._queue: Optional[str] = None
    #     self.re_build: bool = False
    #     self.current_embeds: List[discord.Embed] = []
    #     self.add_item(SelectMatchHistoryX(self))

    # @staticmethod
    # def tier_embed(mmr: Optional[valorantx.MMR] = None) -> Optional[discord.Embed]:
    #     if mmr is None:
    #         return None
    #     competitive = mmr.get_latest_competitive_season()
    #     if competitive is not None:
    #         parent_season = competitive.season.parent
    #         e = discord.Embed(colour=int(competitive.tier.background_color[:-2], 16), timestamp=datetime.datetime.now())
    #         e.set_author(name=competitive.tier.display_name, icon_url=competitive.tier.large_icon)
    #         e.set_footer(
    #             text=str(competitive.ranked_rating)
    #             + '/100'
    #             + ' • '
    #             + parent_season.display_name
    #             + ' '
    #             + competitive.season.display_name
    #         )
    #         return e
    #     return None

    # async def start_pages(self, *, content: Optional[str] = None, ephemeral: bool = False) -> None:
    #     await super().start_pages(content=content, ephemeral=ephemeral)

    # async def start_view(self, riot_auth: RiotAuth, **kwargs: Any) -> None:
    #     self._queue = kwargs.pop('queue', self._queue)
    #     client = self.v_client.set_authorize(riot_auth)
    #     match_history = await client.fetch_match_history(queue=self._queue)  # type: ignore
    #     self.source = CarrierPageSourceX(data=match_history.get_match_details())
    #     # self.mmr = await client.fetch_mmr(riot_auth)
    #     # TODO: build tier embed
    #     await self.start_pages()

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        riot_auth: Optional[RiotAuth] = self.get_riot_auth(interaction.extras.get('puuid'))
        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get gamepass without account')
            return

        match_history = await self.valorant_client.fetch_match_history(
            puuid=riot_auth.puuid,
            queue=self.queue_id,
            with_details=True,
            riot_auth=riot_auth,
        )
        # mmr = await client.fetch_mmr(riot_auth)
        self.source = CarrierPageSource(puuid=riot_auth.puuid, data=match_history.match_details)  # type: ignore

        await self.start()


# match details


class MatchDetailsPageSource(ListPageSource):
    def __init__(self, match_details: MatchDetails, puuid: str) -> None:
        # total_pages = 2
        # if match_details.match_info._game_mode_url != GameModeURL.deathmatch.value:
        #     total_pages += 1
        entries: List[Tuple[Any, Any]] = []
        embeds = e.MatchEmbed(match_details, puuid)
        for dt, mb in zip(embeds.get_desktop(), embeds.get_mobile()):
            entries.append((dt, mb))
        super().__init__(entries, per_page=1)

    def format_page(self, menu: MatchDetailsView, entries: Tuple[Embed, Embed]) -> Embed:
        desktop, mobile = entries
        return mobile if menu.is_on_mobile() else desktop
        # return self.mobile[entries] if menu.is_on_mobile else self.desktop[entries]


class MatchDetailsView(ViewAuthor, LattePages, Generic[ViewT]):
    __view_on_mobile__: bool = False

    def __init__(
        self,
        # source: MatchDetailsPageSource,
        interaction: Interaction[LatteMaid],
        other_view: Optional[ViewT] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(interaction, *args, **kwargs)
        # self.source = source
        self.other_view: Optional[ViewT] = other_view
        if self.other_view is None:
            self.remove_item(self.back_to_home)

    def is_on_mobile(self) -> bool:
        return self.__view_on_mobile__

    @ui.button(emoji='🖥️', style=ButtonStyle.green, custom_id='mobile', row=0)
    async def toggle_ui(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
        button.emoji = '🖥️' if self.is_on_mobile() else '📱'
        self.__view_on_mobile__ = not self.is_on_mobile()
        await self.show_checked_page(interaction, 0)

    @ui.button(label=_("Home"), style=ButtonStyle.green, custom_id='home_button')
    async def back_to_home(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
        await interaction.response.defer()

        if self.message is None:
            return

        if self.other_view is not None:
            self.other_view.reset_timeout()

        # await self.message.edit(embeds=self.other_view.current_embeds, view=self.other_view)

    # async def start(self, match: valorantx.MatchDetails) -> None:
    #     self.source = MatchDetailsPageSourceX(match)
    #     await self.start_pages()


# class MatchDetailsSwitchX(BaseSwitchView, MatchDetailsView):
#     def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
#         super().__init__(interaction, account_manager, 1)

#     # def __init__(self, interaction: Interaction, v_user: ValorantUser, client: ValorantClient) -> None:
#     #     super().__init__(interaction, v_user=v_user, client=client, row=2)
#     #     self._queue: Optional[str] = None

#     async def start_view(self, riot_auth: RiotAuth, **kwargs: Any) -> None:
#         self._queue = kwargs.pop('queue', self._queue)
#         client = self.v_client.set_authorize(riot_auth)
#         match_history = await client.fetch_match_history(queue=self._queue, start=0, end=1)  # type: ignore

#         if len(match_history.get_match_details()) == 0:
#             self.disable_buttons()
#             embed = discord.Embed(
#                 title=_("No matches found"),
#                 description=_("You have no matches in your match history"),
#                 color=discord.Color.red(),
#             )
#             if self.message is None:
#                 self.message = await self.interaction.edit_original_response(embed=embed, view=self)
#             await self.message.edit(embed=embed, view=self)
#             return
#         self.current_page = 0
#         await super().start(match=match_history.get_match_details()[0])

#     def disable_buttons(self):
#         self.previous_page.disabled = self.next_page.disabled = self.toggle_ui.disabled = True

#     async def on_timeout(self) -> None:
#         self.clear_items()
#         await super().on_timeout()
