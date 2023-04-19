from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

# fmt: off
from valorantx2.valorant_api.models import (
    CompetitiveTier as ValorantAPICompetitiveTier,
    ContentTier as ValorantAPIContentTier,
    Tier as ValorantAPITier,
)

from ..emojis import get_content_tier_emoji, get_tier_emoji

# fmt: on

if TYPE_CHECKING:
    from valorantx2.valorant_api.types.competitive_tiers import CompetitiveTier as CompetitiveTierPayload

    from ..valorant_api_cache import Cache

__all__: Tuple[str, ...] = (
    'Tier',
    'ContentTier',
    'CompetitiveTier',
)


class Tier(ValorantAPITier):
    @property
    def emoji(self) -> str:
        # will not be used as a tier number because each season's rank is different
        return get_tier_emoji(self.display_name.default)


class ContentTier(ValorantAPIContentTier):
    @property
    def emoji(self) -> str:
        return get_content_tier_emoji(self.dev_name)


class CompetitiveTier(ValorantAPICompetitiveTier):
    def __init__(self, state: Cache, data: CompetitiveTierPayload) -> None:
        super().__init__(state, data)
        self._tiers: List[Tier] = [Tier(state=self._state, data=tier) for tier in data['tiers']]
