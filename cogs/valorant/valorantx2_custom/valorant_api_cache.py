from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx2.valorant_api_cache import CacheState as ValorantAPICacheState

from .custom import ContentTier

if TYPE_CHECKING:
    from valorantx2.valorant_api.types import content_tiers


class Cache(ValorantAPICacheState):
    def store_content_tier(self, data: content_tiers.ContentTier) -> ContentTier:
        content_tier_id = data['uuid']
        self._content_tiers[content_tier_id] = content_tier = ContentTier(state=self, data=data)
        return content_tier
