from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord

from core.ui.embed import MiadEmbed as Embed
from core.utils.pages import LattePages, ListPageSource
from valorantx2.enums import RelationType
from valorantx2.models import PlayerCard, PlayerTitle, SkinLevel

from ..utils import locale_converter
from .base import BaseView

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2.models import Contract, RewardValorantAPI  # MatchDetails,; MatchHistory,


class GamePassEmbed:
    def __init__(
        self,
        contract: Contract,
        riot_id: str,
        *,
        locale: discord.Locale,
    ) -> None:
        self.contract: Contract = contract
        self.riot_id: str = riot_id
        self.locale: discord.Locale = locale
        self.title: str = ''  # TODO: localize
        if self.contract.content.relation_type is RelationType.agent:
            self.title = 'Agent'
        elif self.contract.content.relation_type is RelationType.season:
            self.title = 'Battlepass'
        elif self.contract.content.relation_type is RelationType.event:
            self.title = 'Eventpass'

    # @cache ?
    def build_page_embed(self, page: int, reward: RewardValorantAPI, locale: discord.Locale | None = None) -> Embed:
        locale = locale or self.locale

        valorant_locale = locale_converter.to_valorant(locale)

        embed = Embed(title=f'{self.title} // {self.riot_id}')
        embed.set_footer(text=f'TIER {page + 1} | {self.contract.display_name_localized(valorant_locale)}')
        item = reward.get_item()
        if item is not None:
            embed.description = item.display_name_localized(valorant_locale)
            if not isinstance(item, PlayerTitle):
                if item.display_icon is not None:
                    if isinstance(item, SkinLevel):
                        embed.set_image(url=item.display_icon)
                    elif isinstance(item, PlayerCard):
                        embed.set_image(url=item.wide_art)
                    # elif isinstance(item, valorantx.Agent):
                    #     embed.set_image(url=item.full_portrait_v2 or item.full_portrait)
                    else:
                        embed.set_thumbnail(url=item.display_icon)
        return embed


class GamePassPageSource(ListPageSource['RewardValorantAPI']):
    def __init__(self, contract: Contract, riot_id: str, locale: discord.Locale) -> None:
        self.embed = GamePassEmbed(contract, riot_id, locale=locale)
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
