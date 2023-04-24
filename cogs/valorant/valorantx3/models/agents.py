from __future__ import annotations

# from functools import cached_property
from typing import TYPE_CHECKING, List

from valorantx2.valorant_api.models import (
    Ability as ValorantAPIAbility,
    Agent as ValorantAPIAgent,
    Media as Media,
    Role as Role,
    VoiceLine as VoiceLine,
    VoiceLineLocalization as VoiceLineLocalization,
)

from ..emojis import get_ability_emoji, get_agent_emoji

if TYPE_CHECKING:
    from valorantx2.valorant_api.types.agents import Agent as AgentPayload

    from ..valorant_api_cache import Cache

__all__ = ('Ability', 'Agent', 'Role', 'Media', 'VoiceLine', 'VoiceLineLocalization')


class Ability(ValorantAPIAbility):
    @property
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

    @property
    def emoji(self) -> str:
        return get_agent_emoji(self.display_name.default)
