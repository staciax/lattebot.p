from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx.valorant_api_cache import CacheState

from .models.custom.agents import Agent
from .models.custom.competitive_tiers import CompetitiveTier
from .models.custom.content_tiers import ContentTier
from .models.custom.currencies import Currency
from .models.custom.gamemodes import GameMode

if TYPE_CHECKING:
    from valorantx.valorant_api.types import agents, competitive_tiers, content_tiers, currencies, gamemodes

# fmt: off
__all__ = (
    'ValorantAPICache',
)
# fmt: on


class ValorantAPICache(CacheState):
    def store_content_tier(self, data: content_tiers.ContentTier) -> ContentTier:
        content_tier_id = data['uuid']
        self._content_tiers[content_tier_id] = content_tier = ContentTier(state=self, data=data)
        return content_tier

    def store_agent(self, data: agents.Agent) -> Agent:
        agent_id = data['uuid']
        self._agents[agent_id] = agent = Agent(state=self, data=data)
        return agent

    def store_currency(self, data: currencies.Currency) -> Currency:
        currency_id = data['uuid']
        self._currencies[currency_id] = currency = Currency(state=self, data=data)
        return currency

    def store_game_mode(self, data: gamemodes.GameMode) -> GameMode:
        game_mode_id = data['uuid']
        self._game_modes[game_mode_id] = game_mode = GameMode(state=self, data=data)
        return game_mode

    def store_competitive_tier(self, data: competitive_tiers.CompetitiveTier) -> CompetitiveTier:
        competitive_tier_id = data['uuid']
        self._competitive_tiers[competitive_tier_id] = competitive_tier = CompetitiveTier(state=self, data=data)
        return competitive_tier
