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

# import core.utils.chat_formatting as chat
from core.bot import LatteMaid
from core.i18n import _
from core.ui.views import ViewAuthor

from .. import valorantx2 as valorantx
from ..valorantx2 import RiotAuth
from ..valorantx2.enums import Locale as ValorantLocale  # , RelationType

# from ..valorantx2.models import FeaturedBundle, RewardValorantAPI, StoreFront, Wallet
from . import embeds as e

# from core.utils.pages import LattePages, ListPageSource


if TYPE_CHECKING:
    from core.bot import LatteMaid

    from ..valorantx2 import Client as ValorantClient

    # from .embeds import Embed

__all__ = ('AccountManager',)


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

    # async def fetch_storefront(self) -> valorantx.StoreFront:
    #     puuid: Optional[str] = None
    #     if self.current_riot_account is not None:
    #         puuid = self.current_riot_account.puuid
    #     if sf := self.valorant_client.get_storefront(puuid):
    #         return sf
    #     return await self.valorant_client.fetch_storefront(self.current_riot_account)

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
            if isinstance(item, ui.Button):
                if item.custom_id != self.custom_id:
                    item.disabled = False

        interaction.extras['puuid'] = self.custom_id
        interaction.extras['label'] = self.label

        await self.view.callback(interaction)


class BaseView(_ViewAuthor):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager)

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


class BaseSwitchView(BaseView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager)
        self._ready: asyncio.Event = asyncio.Event()
        asyncio.create_task(self._initialize())

    async def _initialize(self) -> None:
        await self.account_manager.init()
        self._build_buttons()
        self._ready.set()

    def _build_buttons(self, row: int = 0) -> None:
        for index, acc in enumerate(self.account_manager.riot_accounts, start=1):
            if index >= 4:
                row += 1
            self.add_item(
                ButtonAccountSwitch(
                    label="Account #" + str(index) if self.account_manager.hide_display_name else acc.display_name,
                    disabled=(index == 1),
                    custom_id=acc.puuid,
                    row=row,
                )
            )

    def remove_switch_button(self) -> None:
        for child in self.children:
            if isinstance(child, ButtonAccountSwitch):
                self.remove_item(child)

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer()


class StoreFrontView(BaseSwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], account_manager: AccountManager) -> None:
        super().__init__(interaction, account_manager)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await super().callback(interaction)

        await self.wait_until_ready()

        riot_auth: Optional[RiotAuth] = None

        if 'puuid' in interaction.extras:
            riot_auth = self.account_manager.get_riot_account(interaction.extras['puuid'])
        else:
            riot_auth = self.account_manager.first_account

        if riot_auth is None:
            _log.error(f'user {interaction.user}({interaction.user.id}) tried to get storefront without account')
            return

        storefront = await self.account_manager.fetch_storefront(riot_auth)

        embeds = e.store_e(
            storefront.skins_panel_layout,
            riot_id=riot_auth.display_name,
            locale=self.account_manager.locale,
        )

        if self.message is not None:
            await self.safe_edit_message(self.message, embeds=embeds, view=self)
            return
        self.message = await interaction.followup.send(embeds=embeds, view=self)
