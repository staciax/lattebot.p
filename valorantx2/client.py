from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import valorantx
from async_lru import alru_cache
from valorantx.client import _authorize_required, _loop
from valorantx.enums import Locale, QueueType
from valorantx.models.contracts import Contracts
from valorantx.models.favorites import Favorites
from valorantx.models.loadout import Loadout
from valorantx.models.mmr import MatchmakingRating
from valorantx.models.party import Party, PartyPlayer
from valorantx.models.store import StoreFront, Wallet
from valorantx.models.user import ClientUser
from valorantx.utils import MISSING

from .auth import RiotAuth
from .http import HTTPClient
from .models import PartialUser, PatchNoteScraper
from .models.custom.match import MatchDetails
from .valorant_api_client import Client as ValorantAPIClient

if TYPE_CHECKING:
    from valorantx.models.match import MatchHistory
    from valorantx.models.patchnotes import PatchNotes
    from valorantx.models.seasons import Season
    from valorantx.models.store import FeaturedBundle
    from valorantx.models.version import Version

    from core.bot import LatteMaid


# fmt: off
__all__ = (
    'Client',
)
# fmt: on

# https://valorant.dyn.riotcdn.net/x/content-catalog/PublicContentCatalog-{branch}.zip


# valorantx Client customized for lattemaid
class Client(valorantx.Client):
    def __init__(self, bot: LatteMaid = MISSING) -> None:
        self.bot: LatteMaid = bot
        self.locale: Locale = valorantx.Locale.english
        self.loop: asyncio.AbstractEventLoop = _loop
        self.http: HTTPClient = HTTPClient(self.loop)
        self.valorant_api: ValorantAPIClient = ValorantAPIClient(self.http._session, self.locale)
        self._closed: bool = False
        self._version: Version = MISSING
        self._ready: asyncio.Event = MISSING
        self._authorized: asyncio.Event = MISSING
        self._season: Season = MISSING
        self._act: Season = MISSING
        self.me: ClientUser = MISSING
        self._tasks: Dict[str, asyncio.Task[None]] = {}
        self.lock: asyncio.Lock = asyncio.Lock()

    # auth related

    @property
    def version(self) -> Version:
        return self._version

    @version.setter
    def version(self, value: Version) -> None:
        self._version = value

    @property
    def season(self) -> Season:
        return self._season

    @season.setter
    def season(self, value: Season) -> None:
        self._season = value

    @property
    def act(self) -> Season:
        return self._act

    @act.setter
    def act(self, value: Season) -> None:
        self._act = value

    # patch note

    @alru_cache(maxsize=32, ttl=60 * 60 * 12)  # ttl 12 hours
    async def fetch_patch_notes(self, locale: Union[Locale, str] = Locale.american_english) -> PatchNotes:
        return await super().fetch_patch_notes(locale)

    @alru_cache(maxsize=64, ttl=60 * 60 * 12)  # ttl 12 hours
    async def fetch_patch_note_from_site(self, url: str) -> PatchNoteScraper:
        """|coro|

        Fetches patch notes from the given url.

        Parameters
        ----------
        url: :class:`str`
            The url to fetch the patch notes from.

        Returns
        -------
        :class:`PatchNoteScraper`
            The patch notes.
        Raises
        ------
        HTTPException
            Fetching the patch notes failed.
        NotFound
            The patch notes were not found.
        Forbidden
            You are not allowed to fetch the patch notes.
        """
        text = await self.http.text_from_url(url)
        return PatchNoteScraper.from_text(self, text)

    # henrikdev

    async def fetch_partial_user(self, name: str, tagline: str) -> Optional[PartialUser]:
        """|coro|

        Fetches a partial user from the given name and tagline.

        Parameters
        ----------
        name: :class:`str`
            The name of the user.
        tagline: :class:`str`
            The tagline of the user.

        Returns
        -------
        Optional[:class:`PartialUser`]
            The partial user or ``None`` if not found.

        Raises
        ------
        HTTPException
            Fetching the partial user failed.
        NotFound
            The partial user was not found.
        Forbidden
            You are not allowed to fetch the partial user.
        RateLimited
            You are being rate limited.
        """
        data = await self.http.get_account(name, tagline)
        if data is None or 'data' not in data:
            return None
        return PartialUser(state=self.valorant_api.cache, data=data['data'])

    # store

    @alru_cache(maxsize=1, ttl=60 * 60 * 12)  # ttl 12 hours
    # @_authorize_required
    async def fetch_featured_bundle(self) -> List[FeaturedBundle]:
        # cache re-use
        # TODO: sort expire time
        for cache in self.fetch_storefront._LRUCacheWrapper__cache.values():  # type: ignore
            if not cache.fut.done():
                continue
            if cache.fut._exception is not None:
                continue
            sf = cache.fut.result()
            if isinstance(sf, StoreFront):
                return sf.bundles

        storefront = await self.fetch_storefront()
        return storefront.bundles

    @alru_cache(maxsize=512, ttl=60 * 60 * 12)  # ttl 12 hours
    async def fetch_storefront(self, riot_auth: Optional[RiotAuth] = None) -> StoreFront:
        if riot_auth is None:
            return await super().fetch_storefront()
        data = await self.http.post_store_storefront_riot_auth(riot_auth)
        return StoreFront(self.valorant_api.cache, data)

    @alru_cache(maxsize=512, ttl=30)  # ttl 30 seconds
    async def fetch_wallet(self, riot_auth: Optional[RiotAuth] = None) -> Wallet:
        if riot_auth is None:
            return await super().fetch_wallet()
        data = await self.http.get_store_wallet_riot_auth(riot_auth)
        return Wallet(state=self.valorant_api.cache, data=data)

    # contracts

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    async def fetch_contracts(self, riot_auth: Optional[RiotAuth] = None) -> Contracts:
        if riot_auth is None:
            return await super().fetch_contracts()
        data = await self.http.get_contracts_riot_auth(riot_auth)
        return Contracts(state=self.valorant_api.cache, data=data)

    # favorites

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    async def fetch_favorites(self, riot_auth: Optional[RiotAuth] = None) -> Favorites:
        if riot_auth is None:
            return await super().fetch_favorites()
        data = await self.http.get_favorites_riot_auth(riot_auth)
        return Favorites(state=self.valorant_api.cache, data=data)

    # match

    @alru_cache(maxsize=512, ttl=60 * 60 * 12)  # ttl 12 hours
    async def fetch_match_details(self, match_id: str) -> MatchDetails:
        # TODO: save data to file or cache?
        data = await self.http.get_match_details(match_id)
        return MatchDetails(client=self, data=data)

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    async def fetch_match_history(
        self,
        puuid: str,  # required puuid
        queue: Optional[Union[str, QueueType]] = None,
        *,
        start: int = 0,
        end: int = 15,
        with_details: bool = True,
    ) -> MatchHistory:
        return await super().fetch_match_history(puuid, queue=queue, start=start, end=end, with_details=with_details)

    # mmr

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    @_authorize_required
    async def fetch_mmr(
        self,
        puuid: Optional[str] = None,
        riot_auth: Optional[RiotAuth] = None,
    ) -> MatchmakingRating:
        if riot_auth is None:
            return await super().fetch_mmr(puuid=puuid)
        data = await self.http.get_mmr_player_riot_auth(puuid, riot_auth=riot_auth)
        return MatchmakingRating(self, data=data)

    # loudout

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    @_authorize_required
    async def fetch_loudout(self, riot_auth: Optional[RiotAuth] = None) -> Loadout:
        if riot_auth is None:
            return await super().fetch_loudout()
        favorites = await self.fetch_favorites(riot_auth)
        data = await self.http.get_personal_player_loadout_riot_auth(riot_auth)
        return Loadout(self, data, favorites=favorites)

    # party

    async def fetch_party_player(self, *, riot_auth: Optional[RiotAuth] = None) -> PartyPlayer:
        if riot_auth is None:
            return await super().fetch_party_player()
        data = await self.http.get_party_player_riot_auth(riot_auth=riot_auth)
        return PartyPlayer(client=self, data=data)

    async def fetch_party(self, party_id: str, *, riot_auth: Optional[RiotAuth] = None) -> Party:
        if riot_auth is None:
            return await super().fetch_party(party_id)
        data = await self.http.get_party_riot_auth(party_id, riot_auth=riot_auth)
        return Party(client=self, data=data)

    async def party_invite_by_riot_id(
        self,
        party_id: str,
        game_name: str,
        tag_line: str,
        *,
        riot_auth: RiotAuth,
    ) -> Party:
        data = await self.http.post_party_invite_by_riot_id_riot_auth(
            party_id,
            game_name,
            tag_line,
            riot_auth=riot_auth,
        )
        return Party(client=self, data=data)

    # cache

    async def cache_clear(self) -> None:
        for method in self.__dict__.values():
            if hasattr(method, 'cache_clear'):
                method.cache_clear()
