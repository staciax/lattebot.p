from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx.valorant_api.models import Ability as ValorantAPIAbility, Agent as ValorantAPIAgent

from ...emojis import get_ability_emoji, get_agent_emoji

__all__ = (
    'Ability',
    'Agent',
)

if TYPE_CHECKING:
    from valorantx.valorant_api.types.agents import Agent as AgentPayload

    from ...valorant_api_cache import ValorantAPICache


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
    def __init__(self, *, state: ValorantAPICache, data: AgentPayload) -> None:
        super().__init__(state=state, data=data)
        self._abilities: dict[str, Ability] = {
            ability['slot'].lower(): Ability(state=self._state, data=ability, agent=self) for ability in data['abilities']
        }

    @property
    def emoji(self) -> str:
        return get_agent_emoji(self.display_name.default)
