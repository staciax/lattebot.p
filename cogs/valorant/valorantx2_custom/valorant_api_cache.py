from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx2.valorant_api_cache import CacheState as ValorantAPICacheState

from .models import Agent, ContentTier

if TYPE_CHECKING:
    from valorantx2.valorant_api.types import agents, content_tiers


class Cache(ValorantAPICacheState):
    def store_content_tier(self, data: content_tiers.ContentTier) -> ContentTier:
        content_tier_id = data['uuid']
        self._content_tiers[content_tier_id] = content_tier = ContentTier(state=self, data=data)
        return content_tier

    def store_agent(self, data: agents.Agent) -> Agent:
        agent_id = data['uuid']
        self._agents[agent_id] = agent = Agent(state=self, data=data)
        return agent
