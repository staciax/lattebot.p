from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx2 import Locale
from valorantx2.valorant_api_client import Client as ValorantAPIClient

from .valorant_api_cache import Cache

if TYPE_CHECKING:
    from aiohttp import ClientSession

# fmt: off
__all__ = (
    'Client',
)
# fmt: on


class Client(ValorantAPIClient):
    def __init__(self, session: ClientSession, locale: Locale = Locale.english) -> None:
        super().__init__(session, locale)
        self._cache: Cache = Cache(locale=locale, http=self._http)
