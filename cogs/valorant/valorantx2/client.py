from typing import Any, Optional, Tuple

import valorantx
from valorantx.client import _authorize_required
from valorantx.ext.scrapers import PatchNote
from valorantx.http import Route

from .custom import Agent, CompetitiveTier, ContentTier, Currency, GameMode, MatchDetails, PartialAccount, Player

# fmt: off
__all__: Tuple[str, ...] = (
    'Client',
)
# fmt: on

# valorantx Client customized for lattemaid


class Client(valorantx.Client):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(locale=valorantx.Locale.thai, **kwargs)
        # self._is_authorized = True
        # self.user = valorantx.utils.MISSING
        # self.lock = asyncio.Lock()

    # patch note

    async def fetch_patch_note_from_site(self, url: str) -> PatchNote:
        text = await self.http.text_from_url(url)
        return PatchNote.from_text(text)

    # --- custom for emoji

    def get_agent(self, *args: Any, **kwargs: Any) -> Optional[Agent]:
        data = self._assets.get_agent(*args, **kwargs)
        return Agent(client=self, data=data) if data else None

    def get_content_tier(self, *args: Any, **kwargs: Any) -> Optional[ContentTier]:
        """:class:`Optional[ContentTier]`: Gets a content tier from the assets."""
        data = self._assets.get_content_tier(*args, **kwargs)
        return ContentTier(client=self, data=data) if data else None

    def get_currency(self, *args: Any, **kwargs: Any) -> Optional[Currency]:
        """:class:`Optional[Currency]`: Gets a currency from the assets."""
        data = self._assets.get_currency(*args, **kwargs)
        return Currency(client=self, data=data) if data else None

    def get_competitive_tier(self, *args: Any, **kwargs: Any) -> Optional[CompetitiveTier]:
        """:class:`Optional[CompetitiveTier]`: Gets a competitive tier from the assets."""
        data = self._assets.get_competitive_tier(*args, **kwargs)
        return CompetitiveTier(client=self, data=data) if data else None

    def get_game_mode(self, *args: Any, **kwargs: Any) -> Optional[GameMode]:
        """:class:`Optional[GameMode]`: Gets a game mode from the assets."""
        data = self._assets.get_game_mode(*args, **kwargs)
        return GameMode(client=self, data=data, **kwargs) if data else None

    @_authorize_required
    async def fetch_match_details(self, match_id: str) -> Optional[MatchDetails]:
        """|coro|

        Fetches the match details for a given match.

        Parameters
        ----------
        match_id: :class:`str`
            The match ID to fetch the match details for.

        Returns
        -------
        Optional[:class:`MatchDetails`]
            The match details for a given match.
        """
        match_details = await self.http.fetch_match_details(match_id)
        return MatchDetails(client=self, data=match_details)

    # --- end custom for emoji

    def http_fetch_account(self, name: str, tagline: str) -> Optional[PartialAccount]:
        class HenrikRoute(Route):
            def __init__(self, method: str, path: str) -> None:
                self.method = method
                self.path = path
                self.url: str = 'https://api.henrikdev.xyz/valorant' + self.path

        route = HenrikRoute('GET', '/v1/account/{name}/{tagline}'.format(name=name, tagline=tagline))
        return self.http.request(route, headers={})

    async def fetch_account(self, name: str, tagline: str) -> Optional[Player]:
        data = await self.http_fetch_account(name, tagline)
        pa = PartialAccount(client=self, data=data['data']) if data else None
        return Player.from_partial_account(self, pa) if pa else None
