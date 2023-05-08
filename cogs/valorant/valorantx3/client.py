from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Coroutine, Dict, List, Optional, TypeVar

import valorantx2 as valorantx
from async_lru import alru_cache
from valorantx2 import Locale
from valorantx2.client import _authorize_required, _loop
from valorantx2.enums import try_enum
from valorantx2.models.user import ClientUser, User
from valorantx2.utils import MISSING
from valorantx2.valorant_api.models.version import Version as ValorantAPIVersion

from .auth import RiotAuth
from .http import HTTPClient
from .models import PartialUser, PatchNoteScraper
from .valorant_api_client import Client as ValorantAPIClient

if TYPE_CHECKING:
    from typing_extensions import Self

# fmt: off
__all__ = (
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
        # global lock
        self._lock: asyncio.Lock = asyncio.Lock()
        # client users
        self._users: Dict[str, User] = {}

    # auth related

    def set_authorize(self, riot_auth: RiotAuth) -> Self:
        # set riot auth
        self.http.riot_auth = riot_auth
        payload = dict(
            puuid=riot_auth.puuid,
            game_name=riot_auth.game_name,
            tag_line=riot_auth.tag_line,
            region=riot_auth.region,
        )
        user = User(data=payload)  # type: ignore
        if user.puuid not in self._users:
            self._users[user.puuid] = user
            # self.loop.create_task(user.update_identities())

        # rebuild headers
        self.loop.create_task(self.http.build_headers())
        return self

    def get_user(self, puuid: str) -> Optional[User]:
        return self._users.get(puuid)

    # patch note

    async def fetch_patch_note_from_site(self, url: str) -> PatchNoteScraper:
        # TODO: doc
        text = await self.http.text_from_url(url)
        return PatchNoteScraper.from_text(self, text)

    # henrikdev

    async def fetch_partial_account(self, name: str, tagline: str) -> Optional[PartialUser]:
        """Fetches a partial user from the API.

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
        if data is None or 'data' not in data:
            return None
        return PartialUser(state=self.valorant_api.cache, data=data['data'])

    @alru_cache(maxsize=1, ttl=60 * 60 * 12)  # ttl 12 hours
    async def fetch_featured_bundle(self) -> List[valorantx.FeaturedBundle]:
        # TODO: cache re-use
        # try:
        #     v_user = await self.fetch_user(id=self.bot.owner_id)  # super user
        # except NoAccountsLinked:
        #     riot_acc = RiotAuth(self.bot.owner_id, self.bot.support_guild_id, bot=self.bot)
        #     await riot_acc.authorize(username=self.bot.riot_username, password=self.bot.riot_password)
        # else:
        #     riot_acc = v_user.get_account()
        data = await self.fetch_storefront()
        return data.bundles

    @_authorize_required
    async def fetch_storefront(self, riot_auth: Optional[RiotAuth] = None) -> valorantx.StoreFront:
        async with self._lock:
            if riot_auth is not None:
                self.set_authorize(riot_auth)
            return await super().fetch_storefront()

    # @_authorize_required
    # async def fetch_match_details(self, match_id: str) -> Optional[MatchDetails]:
    #     match_details = await self.http.get_match_details(match_id)
    #     return MatchDetails(client=self, data=match_details)

    @_authorize_required
    async def fetch_contracts(self, riot_auth: Optional[RiotAuth] = None) -> valorantx.Contracts:
        async with self._lock:
            if riot_auth is not None:
                self.set_authorize(riot_auth)
            return await super().fetch_contracts()

    # @_authorize_required
    # async def fetch_mmr(self, puuid: Optional[str] = None, *, riot_auth: RiotAuth) -> valorantx.MMR:
    #     async with self._lock:
    #         # self.set_authorize(riot_auth)
    #         return await super().fetch_mmr(puuid=puuid)
