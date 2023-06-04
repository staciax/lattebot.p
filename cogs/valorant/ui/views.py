from __future__ import annotations

# import abc
# import contextlib
import asyncio
import logging

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

# from ..valorantx2.models import FeaturedBundle, RewardValorantAPI, StoreFront, Wallet
from . import embeds as e

if TYPE_CHECKING:
    from core.bot import LatteMaid

    from ..valorantx2 import Client as ValorantClient
    from ..valorantx2.models import RewardValorantAPI
    from .embeds import Embed

__all__ = (
    'AccountManager',
    'StoreFrontView',
    'NightMarketView',
    'WalletView',
    'GamePassView',
)


_log = logging.getLogger(__name__)


class AccountManager:
    def __init__(
        self,
        user_id: int,
        valorant_client: ValorantClient,
        *,
        locale: ValorantLocale = ValorantLocale.american_english,
    ) -> None:
        self.user_id: int = user_id
        self.locale: ValorantLocale = locale
        self.valorant_client: ValorantClient = valorant_client
        self.first_account: Optional[RiotAuth] = None
        self._riot_accounts: Dict[str, RiotAuth] = {}
        self._hide_display_name: bool = False
        self._ready: asyncio.Event = asyncio.Event()

    async def init(self) -> None:
        assert self.valorant_client.bot is not None
        user = await self.valorant_client.bot.db.get_user(self.user_id)

        if user is None:
            _log.info(f'User {self.user_id!r} not found in database. creating new user.')
            user = await self.valorant_client.bot.db.create_user(id=self.user_id, locale=self.locale.value)

        for index, riot_account in enumerate(sorted(user.riot_accounts, key=lambda x: x.created_at)):
            riot_auth = RiotAuth.from_db(riot_account)
            self._riot_accounts[riot_auth.puuid] = riot_auth
            if index == 0:
                self.first_account = riot_auth
        self._ready.set()

    @property
    def hide_display_name(self) -> bool:
        return self._hide_display_name

    def is_ready(self) -> bool:
        return self._ready.is_set()

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    @property
    def riot_accounts(self) -> List[RiotAuth]:
        return list(self._riot_accounts.values())

    def get_riot_account(self, puuid: Optional[str]) -> Optional[RiotAuth]:
        return self._riot_accounts.get(puuid)  # type: ignore

    async def fetch_storefront(self, riot_auth: RiotAuth) -> valorantx.StoreFront:
        if sf := self.valorant_client.get_storefront(riot_auth.puuid):
            return sf
        return await self.valorant_client.fetch_storefront(riot_auth)

    def set_locale_from_discord(self, locale: discord.Locale) -> None:
        self.locale = valorantx.utils.locale_converter(locale)


class _ViewAuthor(ViewAuthor):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction)
        self.account_manager: AccountManager = account_manager

    async def interaction_check(self, interaction: discord.Interaction[LatteMaid], /) -> bool:
        if await super().interaction_check(interaction):
            self.account_manager.set_locale_from_discord(interaction.locale)
            return True
        return False


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


class BaseView(_ViewAuthor):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        account_manager: AccountManager,
        *,
        check_embeds: bool = True,
    ) -> None:
        super().__init__(interaction, account_manager)
        self.check_embeds: bool = check_embeds

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


class BaseSwitchView(BaseView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager)
        self._ready: asyncio.Event = asyncio.Event()
        self.row: int = 0
        asyncio.create_task(self._initialize())

    async def _initialize(self) -> None:
        await self.account_manager.init()
        self._build_buttons()
        self._ready.set()

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
        self.hide: bool = hide
        self.front_embed: Optional[Embed] = None
        self.prompt_embeds: Optional[List[Embed]] = None
        self.embeds: Optional[List[Embed]] = None
        self.current_opened: int = 1
        if not hide:
            self.remove_item(self.open_button)
            self.remove_item(self.open_all_button)

    @ui.button(label="Open Once", style=discord.ButtonStyle.primary)
    async def open_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        assert self.message is not None
        if self.embeds is None:
            return
        if self.current_opened > len(self.embeds):
            return
        if self.prompt_embeds is None:
            return

        embeds = []
        embeds.extend(self.embeds[: self.current_opened])
        embeds.extend(self.prompt_embeds[self.current_opened :])
        embeds.insert(0, self.front_embed)

        if self.current_opened == len(self.embeds):
            self.clear_items()

        try:
            await self.message.edit(embeds=embeds, view=self)
        except (discord.errors.HTTPException, discord.errors.Forbidden, discord.errors.NotFound):
            pass
        else:
            self.current_opened += 1

    @ui.button(label="Open All", style=discord.ButtonStyle.primary)
    async def open_all_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        assert self.message is not None
        if self.embeds is None:
            return
        if self.current_opened > len(self.embeds):
            return
        if self.prompt_embeds is None:
            return

        embeds = [self.front_embed, *self.embeds]
        self.clear_items()

        try:
            await self.message.edit(embeds=embeds, view=self)
        except (discord.errors.HTTPException, discord.errors.Forbidden, discord.errors.NotFound):
            pass

    async def on_timeout(self) -> None:
        # if self.embeds is None:
        #     return
        self.remove_item(self.open_button)
        self.remove_item(self.open_all_button)
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

        self.front_embed = front_embed = e.nightmarket_front_e(
            storefront.bonus_store, riot_auth, locale=self.account_manager.locale
        )
        self.embeds = embeds = [
            e.skin_e(skin, locale=self.account_manager.locale) for skin in storefront.bonus_store.skins
        ]

        if self.hide:
            self.prompt_embeds = prompt_embeds = [
                e.skin_e_hide(skin, locale=self.account_manager.locale) for skin in storefront.bonus_store.skins
            ]
            await self.send(embeds=[front_embed, *prompt_embeds])
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


class GamePassPageSource(ListPageSource['RewardValorantAPI']):
    def __init__(self, contract: valorantx.Contract, riot_auth: RiotAuth, locale: ValorantLocale) -> None:
        self.embed = e.GamePassEmbed(contract, riot_auth, locale=locale)
        super().__init__(contract.content.get_all_rewards(), per_page=1)

    async def format_page(self, menu: GamePassView, page: Any):
        reward = self.entries[menu.current_page]
        return self.embed.build_page_embed(menu.current_page, reward, locale=menu.account_manager.locale)


class GamePassView(BaseSwitchView, LattePages):
    embed: e.GamePassEmbed

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
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get storefront without account')
            return

        contracts = await self.account_manager.valorant_client.fetch_contracts(riot_auth)

        contract = (
            contracts.special_contract
            if self.relation_type == RelationType.agent
            else contracts.get_latest_contract(self.relation_type)
        )
        if contract is None:
            raise AppCommandError(f"{chat.bold(self.relation_type.value)} is not available.")

        self.source = GamePassPageSource(contract, riot_auth, locale=self.account_manager.locale)
        await self.start(page_number=contract.current_level)
