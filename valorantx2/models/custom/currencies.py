from valorantx.valorant_api.models import Currency as ValorantAPICurrency

from ...emojis import get_currency_emoji

# fmt: off
__all__ = (
    'Currency',
)
# fmt: on


class Currency(ValorantAPICurrency):
    @property
    def emoji(self) -> str:
        return get_currency_emoji(self.uuid)
