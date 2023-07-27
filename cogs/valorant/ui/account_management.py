# from __future__ import annotations
#
# from pathlib import Path
# from typing import TYPE_CHECKING, Any, TypeVar
#
# import discord
# from discord import ui
# from discord.components import SelectOption
# from discord.enums import Locale
#
# from core.i18n import I18n
# from core.ui.views import ViewAuthor
#
# from ..account_manager import AccountManager
#
# if TYPE_CHECKING:
#     from typing_extensions import Self
#
#     from core.bot import LatteMaid
#     from valorantx2.client import Client as ValorantClient
#
# V = TypeVar('V', bound='ui.View', covariant=True)
#
# _ = I18n('valorant.ui.account_management', Path(__file__).resolve().parent, read_only=True)
#
#
# class AccountSelect(ui.Select[V]):
#     def __init__(
#         self,
#         *,
#         options: list[SelectOption],
#         row: int | None = None,
#         locale: Locale | None = None,
#         **kwargs: Any,
#     ) -> None:
#         super().__init__(
#             placeholder=_('account_select_placeholder', locale),
#             options=options or [SelectOption(label=_('account_select_no_account'), value='no_account')],
#             disabled=not options,
#             row=row,
#             **kwargs,
#         )
#         self.current_puuid: str | None = None
#
#     async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
#         assert self.view is not None
#         value = interaction.extras['puuid'] = self.values[0]
#
#         # if value == 'no_account':
#         #     return
#
#         if self.current_puuid == value:
#             return
#
#         try:
#             await self.view.switch_account_to(value)
#         except (discord.HTTPException, discord.NotFound):
#             pass
#         else:
#             self.current_puuid = value
#
#     # self.current_puuid = value
#
#     @classmethod
#     def from_account_manager(
#         cls,
#         account_manager: AccountManager,
#         row: int = 0,
#         locale: Locale | None = None,
#     ) -> Self:
#         options = [
#             SelectOption(label=account.display_name or account.riot_id, value=account.puuid)
#             for account in account_manager.accounts
#         ]
#         if account_manager.author.locale is not None:
#             locale = discord.Locale(account_manager.author.locale)
#         return cls(options=options, row=row, locale=locale)
#
#
# class BaseView(ViewAuthor):
#     def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
#         super().__init__(interaction)
#         self.account_manager: AccountManager | None = None
#
#     @property
#     def valorant_client(self) -> ValorantClient:
#         return self.bot.valorant_client
#
#     def _fill_account_select(self) -> None:
#         if self.account_manager is None:
#             return
#
#         if not len(self.account_manager.accounts):
#             return
#
#         # move all children down by 1
#         for item in self.children:
#             item.row += 1
#
#         self.add_item(
#             AccountSelect.from_account_manager(
#                 account_manager=self.account_manager,
#                 locale=self.locale,
#             )
#         )
#
#     async def _init(self) -> None:
#         user = await self.bot.db.fetch_user(self.author.id)
#         if user is None:
#             return
#         self.account_manager = AccountManager(user, re_authorize=False)
#         await self.account_manager.wait_until_ready()
#         self._fill_account_select()
#
#     async def switch_account_to(self, puuid: str, /) -> None:
#         pass
#
#     async def start(self) -> None:
#         await self._init()
