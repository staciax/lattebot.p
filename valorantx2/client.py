from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, overload

import valorantx
from async_lru import alru_cache
from valorantx.client import _loop
from valorantx.enums import Locale, QueueType
from valorantx.models.contracts import Contracts
from valorantx.models.favorites import Favorites
from valorantx.models.loadout import Loadout
from valorantx.models.mmr import MatchmakingRating
from valorantx.models.party import Party, PartyPlayer
from valorantx.models.store import AgentStore as _AgentStore, StoreFront, Wallet
from valorantx.models.user import ClientUser
from valorantx.utils import MISSING

from .http import HTTPClient
from .models import PartialUser, PatchNoteScraper
from .models.custom.match import MatchDetails
from .models.custom.store import AgentStore
from .valorant_api_client import Client as ValorantAPIClient

if TYPE_CHECKING:
    from valorantx.models.match import MatchHistory
    from valorantx.models.patchnotes import PatchNotes
    from valorantx.models.seasons import Season
    from valorantx.models.store import FeaturedBundle
    from valorantx.models.version import Version

    from core.bot import LatteMaid

    from .auth import RiotAuth


# fmt: off
__all__ = (
    'Client',
)
# fmt: on

_log = logging.getLogger(__name__)

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
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self.lock: asyncio.Lock = asyncio.Lock()

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
    async def fetch_patch_notes(self, locale: Locale | str = Locale.american_english) -> PatchNotes:
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

    async def fetch_partial_user(self, name: str, tagline: str) -> PartialUser:
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
        :class:`PartialUser`
            The partial user that was fetched.

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
        return PartialUser(self.valorant_api.cache, data['data'])

    # store

    @alru_cache(maxsize=1, ttl=60 * 60 * 12)  # ttl 12 hours
    async def fetch_featured_bundle(self) -> list[FeaturedBundle]:
        # TODO: sort remaining time
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
    async def fetch_storefront(self, riot_auth: RiotAuth | None = None) -> StoreFront:
        data = await self.http.post_store_storefront(riot_auth=riot_auth)
        return StoreFront(self.valorant_api.cache, data)

    @overload
    async def fetch_agent_store(self, riot_auth: RiotAuth) -> AgentStore:
        ...

    @overload
    async def fetch_agent_store(self) -> _AgentStore:
        ...

    async def fetch_agent_store(self, riot_auth: RiotAuth | None = None) -> AgentStore | _AgentStore:
        data = await self.http.get_store_storefronts_agent(riot_auth=riot_auth)
        return AgentStore(self, data['AgentStore'])

    @alru_cache(maxsize=512, ttl=30)  # ttl 30 seconds
    async def fetch_wallet(self, riot_auth: RiotAuth | None = None) -> Wallet:
        data = await self.http.get_store_wallet(riot_auth=riot_auth)
        return Wallet(self.valorant_api.cache, data)

    # contracts

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    async def fetch_contracts(self, riot_auth: RiotAuth | None = None) -> Contracts:
        data = await self.http.get_contracts(riot_auth=riot_auth)
        return Contracts(self, data)

    # favorites

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    async def fetch_favorites(self, riot_auth: RiotAuth | None = None) -> Favorites:
        data = await self.http.get_favorites(riot_auth=riot_auth)
        return Favorites(self.valorant_api.cache, data)

    # match

    @alru_cache(maxsize=512, ttl=60 * 60 * 12)  # ttl 12 hours
    async def fetch_match_details(self, match_id: str) -> MatchDetails:
        # TODO: save data to file or cache?
        data = await self.http.get_match_details(match_id)
        return MatchDetails(self, data)

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    async def fetch_match_history(
        self,
        puuid: str,  # required puuid
        queue: str | QueueType | None = None,
        *,
        start: int = 0,
        end: int = 15,
        with_details: bool = True,
    ) -> MatchHistory:
        return await super().fetch_match_history(puuid, queue=queue, start=start, end=end, with_details=with_details)

    # mmr

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    async def fetch_mmr(
        self,
        puuid: str | None = None,
        riot_auth: RiotAuth | None = None,
    ) -> MatchmakingRating:
        data = await self.http.get_mmr_player(puuid, riot_auth=riot_auth)
        return MatchmakingRating(self, data)

    # loudout

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    async def fetch_loudout(self, riot_auth: RiotAuth | None = None) -> Loadout:
        favorites = await self.fetch_favorites(riot_auth)
        data = await self.http.get_personal_player_loadout(riot_auth=riot_auth)
        return Loadout(self, data, favorites=favorites)

    # party

    async def fetch_party_player(self, *, riot_auth: RiotAuth | None = None) -> PartyPlayer:
        data = await self.http.get_party_player(riot_auth=riot_auth)
        return PartyPlayer(client=self, data=data)

    async def fetch_party(self, party_id: str, *, riot_auth: RiotAuth | None = None) -> Party:
        data = await self.http.get_party(party_id=party_id, riot_auth=riot_auth)
        return Party(self, data)

    async def party_invite_by_riot_id(
        self,
        party_id: str,
        game_name: str,
        tag_line: str,
        *,
        riot_auth: RiotAuth,
    ) -> Party:
        data = await self.http.post_party_invite_by_riot_id(
            party_id,
            game_name,
            tag_line,
            riot_auth=riot_auth,
        )
        return Party(self, data)

    # cache

    async def cache_clear(self) -> None:
        for method_name in dir(self):
            if method_name.startswith('_'):
                continue
            method = getattr(self, method_name)
            if hasattr(method, 'cache_clear'):
                method.cache_clear()

        _log.info('cache cleared')
