from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, List, Tuple

# fmt: off
from valorantx2.valorant_api.models import (
    Ability as ValorantAPIAbility,
    Agent as ValorantAPIAgent,
    CompetitiveTier as ValorantAPICompetitiveTier,
    ContentTier as ValorantAPIContentTier,
    Tier as ValorantAPITier,
)

from ..emojis import get_ability_emoji, get_agent_emoji, get_content_tier_emoji, get_tier_emoji

# fmt: on

if TYPE_CHECKING:
    from valorantx2.valorant_api.types.agents import Agent as AgentPayload
    from valorantx2.valorant_api.types.competitive_tiers import CompetitiveTier as CompetitiveTierPayload

    from ..valorant_api_cache import Cache

__all__: Tuple[str, ...] = (
    'Agent',
    'Tier',
    'ContentTier',
    'CompetitiveTier',
)


class Ability(ValorantAPIAbility):
    @cached_property
    def emoji(self) -> str:
        key = (
            (self.agent.display_name.default.lower() + '_' + self.display_name.default.lower())
            .replace('/', '_')
            .replace(' ', '_')
            .replace('___', '_')
            .replace('__', '_')
            .replace("'", '')
        )
        return get_ability_emoji(key)


class Agent(ValorantAPIAgent):
    def __init__(self, *, state: Cache, data: AgentPayload) -> None:
        super().__init__(state=state, data=data)
        self._abilities: List[Ability] = [
            Ability(state=state, data=ability, agent=self) for ability in data['abilities']
        ]

    @cached_property
    def emoji(self) -> str:
        return get_agent_emoji(self.display_name.default)


class Tier(ValorantAPITier):
    @cached_property
    def emoji(self) -> str:
        # will not be used as a tier number because each season's rank is different
        return get_tier_emoji(self.display_name.default)


class ContentTier(ValorantAPIContentTier):
    @cached_property
    def emoji(self) -> str:
        return get_content_tier_emoji(self.dev_name)


class CompetitiveTier(ValorantAPICompetitiveTier):
    def __init__(self, state: Cache, data: CompetitiveTierPayload) -> None:
        super().__init__(state, data)
        self._tiers: List[Tier] = [Tier(state=self._state, data=tier) for tier in data['tiers']]
