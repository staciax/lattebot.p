from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx import Locale
from valorantx.valorant_api_client import Client

from .valorant_api_cache import ValorantAPICache

# fmt: off
__all__ = (
    'ValorantAPIClient',
)
# fmt: on

if TYPE_CHECKING:
    from aiohttp import ClientSession


class ValorantAPIClient(Client):
    def __init__(self, session: ClientSession, locale: Locale = Locale.english) -> None:
        super().__init__(session, locale)
        self.cache: ValorantAPICache = ValorantAPICache(locale=locale, http=self.http)
