import asyncio
from typing import Any, Coroutine, Optional, Tuple, TypeVar

import valorantx2 as valorantx
from valorantx2 import Locale
from valorantx2.client import _loop  # _authorize_required
from valorantx2.enums import try_enum
from valorantx2.models.user import ClientUser
from valorantx2.utils import MISSING
from valorantx2.valorant_api.models.version import Version as ValorantAPIVersion

from .http import HTTPClient
from .models import PartialAccount
from .valorant_api_client import Client as ValorantAPIClient

# from valorantx2.ext.scrapers import PatchNote
# from .custom import Agent, CompetitiveTier, ContentTier, Currency, GameMode, MatchDetails, PartialAccount, Player

# fmt: off
__all__: Tuple[str, ...] = (
    'Client',
)
# fmt: on

T = TypeVar('T')
Response = Coroutine[Any, Any, T]


# valorantx Client customized for lattemaid
class Client(valorantx.Client):
    def __init__(self, locale=valorantx.Locale.english) -> None:
        self.locale: Locale = try_enum(Locale, locale) if isinstance(locale, str) else locale
        self.loop: asyncio.AbstractEventLoop = _loop
        self.http: HTTPClient = HTTPClient(self.loop)
        self.valorant_api: ValorantAPIClient = ValorantAPIClient(self.http._session, self.locale)
        self._closed: bool = False
        self._is_authorized: bool = True  # default is False but we want to skip auth
        self._version: ValorantAPIVersion = MISSING
        self._ready: asyncio.Event = MISSING
        self.me: ClientUser = MISSING
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

    async def fetch_partial_account(self, name: str, tagline: str) -> Optional[PartialAccount]:
        """Fetches a partial account from the API.

        Parameters
        ----------
        name: :class:`str`
            The name of the account.
        tagline: :class:`str`
            The tagline of the account.

        Returns
        -------
        Optional[:class:`PartialAccount`]
            The partial account fetched from the API.
        Raises
        ------
        HTTPException
            An error occurred while fetching the account.
        NotFound
            The account was not found.
        """
        data = await self.http.get_partial_account(name, tagline)
        if data is None:
            return None
        if 'data' not in data:
            return None
        return PartialAccount(state=self.valorant_api._cache, data=data['data'])
