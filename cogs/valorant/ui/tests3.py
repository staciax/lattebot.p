from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, TypeVar, Union

import discord
from async_lru import alru_cache
from discord import ui
from discord.enums import ButtonStyle

import core.utils.chat_formatting as chat
from cogs.valorant.ui.tests2 import ValorantPageSource
from core.bot import LatteMiad
from core.errors import AppCommandError
from core.translator import _
from core.ui.embed import MiadEmbed as Embed
from core.ui.views import BaseView, ViewAuthor
from core.utils.database.models import User as DBUser
from core.utils.pages import LattePages, ListPageSource, PageSource
from valorantx2.auth import RiotAuth
from valorantx2.client import Client as ValorantClient
from valorantx2.enums import Locale as ValorantLocale, RelationType
from valorantx2.utils import MISSING, locale_converter

from ..account_manager import AccountManager

# from ..account_manager import AccountManager
from . import embeds as e

if TYPE_CHECKING:
    from core.bot import LatteMiad
    from valorantx2.models import Contract, RewardValorantAPI

T = TypeVar('T')
ViewT = TypeVar('ViewT', bound=BaseView)

_log = logging.getLogger(__name__)


class ValorantPageSource(PageSource):
    async def _prepare_once(self):
        try:
            # Don't feel like formatting hasattr with
            # the proper mangling
            # read this as follows:
            # if hasattr(self, '__prepare')
            # except that it works as you expect
            self.__prepare  # type: ignore
        except AttributeError:
            await self.prepare()
            self.__prepare = True

    async def prepare(self):
        return

    def is_paginating(self):
        raise NotImplementedError

    def get_max_pages(self) -> Optional[int]:
        return None

    async def get_page(self, page_number: int) -> Any:
        raise NotImplementedError

    async def format_page(
        self,
        menu: Any,
        entries: Any,
        riot_auth: RiotAuth,
    ) -> Union[discord.Embed, str, Dict[Any, Any]]:
        raise NotImplementedError


class ValorantListPageSource(ValorantPageSource, Generic[T]):
    def __init__(self, entries: List[T], per_page: int = 12) -> None:
        self.entries = entries
        self.per_page = per_page
        pages, left_over = divmod(len(entries), per_page)
        if left_over:
            pages += 1

        self._max_pages = pages

    def is_paginating(self) -> bool:
        return len(self.entries) > self.per_page

    def get_max_pages(self) -> int:
        return self._max_pages

    async def get_page(self, page_number: int) -> Union[Any, List[Any]]:
        if self.per_page == 1:
            return self.entries[page_number]
        else:
            base = page_number * self.per_page
            return self.entries[base : base + self.per_page]


class ButtonAccountSwitch(ui.Button['ValorantSwitchAccountView']):
    def __init__(
        self,
        *,
        label: Optional[str] = None,
        disabled: bool = False,
        custom_id: Optional[str] = None,
        row: Optional[int] = None,
    ) -> None:
        super().__init__(style=discord.ButtonStyle.gray, label=label, disabled=disabled, custom_id=custom_id, row=row)

    async def callback(self, interaction: discord.Interaction[LatteMiad]) -> None:
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

            await self.view.switch_account(interaction, self.custom_id)


class ValorantSwitchAccountView(ViewAuthor):
    def __init__(
        self,
        user: DBUser,
        source: ValorantPageSource = MISSING,
        *,
        interaction: discord.Interaction[LatteMiad],
        row: int = 0,
        check_accounts: bool = True,
    ) -> None:
        super().__init__(interaction)
        self._user = user
        self.account_manager: AccountManager = AccountManager(user, self.bot)
        self.source: ValorantPageSource = source
        self.row = row
        self.check_accounts: bool = check_accounts
        self.lock: asyncio.Lock = asyncio.Lock()

    @property
    def user(self) -> DBUser:
        return self._user

    @property
    def valorant_client(self) -> ValorantClient:
        return self.bot.valorant_client

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

    async def on_timeout(self) -> None:
        if self.message is None:
            try:
                self.message = await self.interaction.original_response()
            except (discord.errors.HTTPException, discord.errors.ClientException, discord.errors.NotFound) as e:
                _log.warning('failed to get original response', exc_info=e)
                return

        self.disable_buttons()
        await self.message.edit(view=self)

    # async def _get_kwargs_from_riot_auth(self, riot_auth: Optional[RiotAuth] = None) -> Dict[str, Any]:
    #     if riot_auth is None:
    #         return {}
    #     value = await discord.utils.maybe_coroutine(self.source.format_page, self, riot_auth)
    #     if isinstance(value, dict):
    #         return value
    #     elif isinstance(value, str):
    #         return {'content': value, 'embed': None}
    #     elif isinstance(value, discord.Embed):
    #         return {'embed': value, 'content': None}
    #     elif isinstance(value, list) and all(isinstance(v, discord.Embed) for v in value):
    #         return {'embeds': value, 'content': None}
    #     else:
    #         return {}

    async def _get_kwargs_from_page(self, page: int, riot_auth: Optional[RiotAuth]) -> Dict[str, Any]:
        if riot_auth is None:
            return {}
        value = await discord.utils.maybe_coroutine(self.source.format_page, self, page, riot_auth)
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

    # async def show_page(self, interaction: discord.Interaction, page_number: int, puuid: Optional[str] = None) -> None:
    #     page = await self.source.get_page(page_number)
    #     riot_auth = self.account_manager.get_riot_account(puuid)
    #     self.current_page = page_number
    #     kwargs = await self._get_kwargs_from_page(page, riot_auth)
    #     # self._update_labels(page_number)
    #     if kwargs:
    #         if interaction.response.is_done():
    #             if self.message:
    #                 await self.message.edit(**kwargs, view=self)
    #         else:
    #             await interaction.response.edit_message(**kwargs, view=self)

    async def switch_account(self, interaction: discord.Interaction[LatteMiad], puuid: Optional[str]) -> None:
        riot_auth = self.account_manager.get_riot_account(puuid)
        # kwargs = await self._get_kwargs_from_riot_auth(riot_auth)
        # if kwargs:
        #     if interaction.response.is_done():
        #         if self.message:
        #             await self.message.edit(**kwargs, view=self)
        #     else:
        #         await interaction.response.edit_message(**kwargs, view=self)

    async def start(self, ephemeral: bool = False) -> None:
        await self.account_manager.init()
        if self.check_accounts and len(self.account_manager.riot_accounts) == 0:
            await self.interaction.response.send_message(_('You have no Valorant accounts registered.'), ephemeral=True)
            return
        self._build_buttons()
        await self.source._prepare_once()

    #     self._build_buttons()
    #     await self.interaction.response.defer(ephemeral=ephemeral)
    #     riot_auth = self.account_manager.first_account
    #     kwargs = await self._get_kwargs_from_riot_auth(riot_auth)
    #     if self.message is not None:
    #         await self.message.edit(**kwargs, view=self)
    #         return
    #     self.message = await self.interaction.followup.send(**kwargs, view=self, ephemeral=ephemeral)


class GamePassPageSource(ValorantListPageSource['RewardValorantAPI']):
    # def __init__(self, contract: Contract, riot_id: str, locale: ValorantLocale) -> None:
    #     super().__init__(contract.content.get_all_rewards(), per_page=1)
    # self.embed = e.GamePassEmbed(contract, riot_id, locale=locale)
    # self.contract = contract

    def __init__(self, contract: Contract, riot_id: str, locale: discord.Locale) -> None:
        super().__init__(contract.content.get_all_rewards(), per_page=1)
        self.embed = e.GamePassEmbed(contract, riot_id, locale=locale_converter.to_valorant(locale))

    async def format_page(self, menu: Any, page: Any, riot_auth: RiotAuth):
        reward = self.entries[menu.current_page]
        return self.embed.build_page_embed(menu.current_page, reward, locale=locale_converter.to_valorant(menu.locale))

    #     contracts = await self.valorant_client.fetch_contracts(riot_auth)

    #     contract = (
    #         contracts.special_contract
    #         if self.relation_type == RelationType.agent
    #         else contracts.get_latest_contract(self.relation_type)
    #     )
    #     self.__init__(contract.content.get_all_rewards(), riot_auth.display_name)
