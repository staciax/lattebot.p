from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx.valorant_api.models import CompetitiveTier as ValorantAPICompetitiveTier, Tier as ValorantAPITier

from ...emojis import get_tier_emoji

if TYPE_CHECKING:
    from valorantx.valorant_api.types.competitive_tiers import CompetitiveTier as CompetitiveTierPayload

    from ...valorant_api_cache import Cache

# fmt: off
__all__ = (
    'Tier',
    'CompetitiveTier',
)
# fmt: on


class Tier(ValorantAPITier):
    @property
    def emoji(self) -> str:
        # will not be used as a tier number because each season's rank is different
        return get_tier_emoji(self.display_name.default)


class CompetitiveTier(ValorantAPICompetitiveTier):
    def __init__(self, state: Cache, data: CompetitiveTierPayload) -> None:
        super().__init__(state, data)
        self._tiers: dict[int, Tier] = {tier['tier']: Tier(state=self._state, data=tier) for tier in data['tiers']}
