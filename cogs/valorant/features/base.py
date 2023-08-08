from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import discord
from discord import Locale, SelectOption, ui

from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from core.ui.views import ViewAuthor
from core.utils.pages import PageSource

from ..account_manager import AccountManager

__all__ = (
    'BaseView',
    'ValorantPageSource',
    'ValorantListPageSource',
    'AccountSelect',
)

if TYPE_CHECKING:
    from typing_extensions import Self

    from core.bot import LatteMaid
    from valorantx2.auth import RiotAuth
    from valorantx2.client import Client as ValorantClient

T = TypeVar('T')
V = TypeVar('V', bound='BaseView', covariant=True)


_log = logging.getLogger(__name__)
_ = I18n('valorant.features.base', Path(__file__).resolve().parent, read_only=True)


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
