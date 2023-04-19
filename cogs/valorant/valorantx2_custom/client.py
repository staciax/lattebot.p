import asyncio
from typing import Tuple  # Any, Optional,

import valorantx2 as valorantx
from valorantx2 import Locale
from valorantx2.client import _loop
from valorantx2.enums import try_enum
from valorantx2.http import HTTPClient
from valorantx2.models.user import ClientUser
from valorantx2.utils import MISSING
from valorantx2.valorant_api.models.version import Version as ValorantAPIVersion

from .valorant_api_client import Client as ValorantAPIClient

# from valorantx2.client import _authorize_required

# from valorantx2.ext.scrapers import PatchNote
# from valorantx2.http import Route

# from .custom import Agent, CompetitiveTier, ContentTier, Currency, GameMode, MatchDetails, PartialAccount, Player

# fmt: off
__all__: Tuple[str, ...] = (
    'Client',
)
# fmt: on


# valorantx Client customized for lattemaid
class Client(valorantx.Client):
    def __init__(self, locale=valorantx.Locale.english) -> None:
        self.locale: Locale = try_enum(Locale, locale) if isinstance(locale, str) else locale
        self.loop: asyncio.AbstractEventLoop = _loop
        self.http: HTTPClient = HTTPClient(self.loop)
        self.valorant_api: ValorantAPIClient = ValorantAPIClient(self.http._session, self.locale)
        self.me: ClientUser = MISSING
        self._closed: bool = False
        self._is_authorized: bool = False
        self._ready: asyncio.Event = MISSING
        self._version: ValorantAPIVersion = MISSING
        self._is_authorized = True
        # self.lock = asyncio.Lock()

    # patch note

    # async def fetch_patch_note_from_site(self, url: str) -> PatchNote:
    #     text = await self.http.text_from_url(url)
    #     return PatchNote.from_text(text)

    # --- custom for emoji

    # def get_agent(self, *args: Any, **kwargs: Any) -> Optional[Agent]:
    #     data = self._assets.get_agent(*args, **kwargs)
    #     return Agent(client=self, data=data) if data else None

    # def get_content_tier(self, *args: Any, **kwargs: Any) -> Optional[ContentTier]:
    #     """:class:`Optional[ContentTier]`: Gets a content tier from the assets."""
    #     data = self._assets.get_content_tier(*args, **kwargs)
    #     return ContentTier(client=self, data=data) if data else None

    # def get_currency(self, *args: Any, **kwargs: Any) -> Optional[Currency]:
    #     """:class:`Optional[Currency]`: Gets a currency from the assets."""
    #     data = self._assets.get_currency(*args, **kwargs)
    #     return Currency(client=self, data=data) if data else None

    # def get_competitive_tier(self, *args: Any, **kwargs: Any) -> Optional[CompetitiveTier]:
    #     """:class:`Optional[CompetitiveTier]`: Gets a competitive tier from the assets."""
    #     data = self._assets.get_competitive_tier(*args, **kwargs)
    #     return CompetitiveTier(client=self, data=data) if data else None

    # def get_game_mode(self, *args: Any, **kwargs: Any) -> Optional[GameMode]:
    #     """:class:`Optional[GameMode]`: Gets a game mode from the assets."""
    #     data = self._assets.get_game_mode(*args, **kwargs)
    #     return GameMode(client=self, data=data, **kwargs) if data else None

    # @_authorize_required
    # async def fetch_match_details(self, match_id: str) -> Optional[MatchDetails]:
    #     match_details = await self.http.fetch_match_details(match_id)
    #     return MatchDetails(client=self, data=match_details)

    # # --- end custom for emoji

    # def http_fetch_account(self, name: str, tagline: str) -> Optional[PartialAccount]:
    #     class HenrikRoute(Route):
    #         def __init__(self, method: str, path: str) -> None:
    #             self.method = method
    #             self.path = path
    #             self.url: str = 'https://api.henrikdev.xyz/valorant' + self.path

    #     route = HenrikRoute('GET', '/v1/account/{name}/{tagline}'.format(name=name, tagline=tagline))
    #     return self.http.request(route, headers={})

    # async def fetch_account(self, name: str, tagline: str) -> Optional[Player]:
    #     data = await self.http_fetch_account(name, tagline)
    #     pa = PartialAccount(client=self, data=data['data']) if data else None
    #     return Player.from_partial_account(self, pa) if pa else None
