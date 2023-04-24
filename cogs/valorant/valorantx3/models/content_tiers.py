from valorantx2.valorant_api.models import ContentTier as ValorantAPIContentTier

from ..emojis import get_content_tier_emoji

# fmt: off
__all__ = (
    'ContentTier',
)
# fmt: on


class ContentTier(ValorantAPIContentTier):
    @property
    def emoji(self) -> str:
        return get_content_tier_emoji(self.dev_name)
