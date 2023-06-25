from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import valorantx
from async_lru import alru_cache
from valorantx.client import _authorize_required, _loop
from valorantx.enums import Locale, QueueType
from valorantx.models.party import Party, PartyPlayer
from valorantx.models.store import StoreFront
from valorantx.models.user import ClientUser
from valorantx.utils import MISSING

from .auth import RiotAuth
from .http import HTTPClient
from .models import PartialUser, PatchNoteScraper
from .models.custom.match import MatchDetails
from .valorant_api_client import Client as ValorantAPIClient

if TYPE_CHECKING:
    from typing_extensions import Self
    from valorantx.models.contracts import Contracts
    from valorantx.models.loadout import Loadout
    from valorantx.models.match import MatchHistory
    from valorantx.models.patchnotes import PatchNotes
    from valorantx.models.seasons import Season
    from valorantx.models.store import FeaturedBundle, Wallet
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
        # client users
        # self._users: Dict[str, User] = {}

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

    async def set_authorize(self, riot_auth: RiotAuth) -> Self:
        # set riot auth
        self.http.riot_auth = riot_auth

        # payload = dict(
        #     puuid=riot_auth.puuid,
        #     game_name=riot_auth.game_name,
        #     tag_line=riot_auth.tag_line,
        #     region=riot_auth.region, # type: ignore
        # )
        # user = User(client=self, data=payload)
        # if user.puuid not in self._users:
        # self._users[user.puuid] = user
        # self.loop.create_task(user.update_identities())

        # rebuild headers
        await self.http.re_build_headers()
        return self

    # def get_user(self, puuid: str) -> Optional[User]:
    #     return self._users.get(puuid)

    # patch note

    @alru_cache(maxsize=32, ttl=60 * 60 * 12)  # ttl 12 hours
    async def fetch_patch_notes(self, locale: str | Locale = Locale.american_english) -> PatchNotes:
        return await super().fetch_patch_notes(locale)

    @alru_cache(maxsize=64, ttl=60 * 60 * 12)  # ttl 12 hours
    async def fetch_patch_note_from_site(self, url: str) -> PatchNoteScraper:
        # TODO: doc
        text = await self.http.text_from_url(url)
        return PatchNoteScraper.from_text(self, text)

    # henrikdev

    async def fetch_partial_account(self, name: str, tagline: str) -> Optional[PartialUser]:
        data = await self.http.get_partial_account(name, tagline)
        if data is None or 'data' not in data:
            return None
        return PartialUser(state=self.valorant_api.cache, data=data['data'])

    @alru_cache(maxsize=1, ttl=60 * 60 * 12)  # ttl 12 hours
    @_authorize_required
    async def fetch_featured_bundle(self) -> List[FeaturedBundle]:
        # cache re-use
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
    @_authorize_required
    async def fetch_storefront(self, riot_auth: Optional[RiotAuth] = None) -> StoreFront:
        async with self.lock:
            if riot_auth is not None:
                await self.set_authorize(riot_auth)
            return await super().fetch_storefront()

    @alru_cache(maxsize=512, ttl=60 * 60 * 12)  # ttl 12 hours
    @_authorize_required
    async def fetch_match_details(self, match_id: str) -> MatchDetails:
        # async with self.lock:
        data = await self.http.get_match_details(match_id)
        # TODO: save data to file or cache?
        return MatchDetails(client=self, data=data)

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    @_authorize_required
    async def fetch_contracts(self, riot_auth: Optional[RiotAuth] = None) -> Contracts:
        async with self.lock:
            if riot_auth is not None:
                await self.set_authorize(riot_auth)
            return await super().fetch_contracts()

    @alru_cache(maxsize=512, ttl=60)  # ttl 1 minute
    @_authorize_required
    async def fetch_wallet(self, riot_auth: Optional[RiotAuth] = None) -> Wallet:
        async with self.lock:
            if riot_auth is not None:
                await self.set_authorize(riot_auth)
            return await super().fetch_wallet()

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    @_authorize_required
    async def fetch_mmr(
        self,
        puuid: Optional[str] = None,
        riot_auth: Optional[RiotAuth] = None,
    ) -> valorantx.MatchmakingRating:
        async with self.lock:
            if riot_auth is not None:
                await self.set_authorize(riot_auth)
            return await super().fetch_mmr(puuid=puuid)

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    @_authorize_required
    async def fetch_loudout(self, riot_auth: Optional[RiotAuth] = None) -> Loadout:
        async with self.lock:
            if riot_auth is not None:
                await self.set_authorize(riot_auth)
            return await super().fetch_loudout()

    @alru_cache(maxsize=512, ttl=60 * 15)  # ttl 15 minutes
    @_authorize_required
    async def fetch_match_history(
        self,
        puuid: Optional[str] = None,
        queue: Optional[Union[str, QueueType]] = None,
        *,
        start: int = 0,
        end: int = 15,
        with_details: bool = True,
        riot_auth: Optional[RiotAuth] = None,
    ) -> MatchHistory:
        if isinstance(queue, QueueType):
            queue = queue.value

        async with self.lock:
            if riot_auth is not None:
                await self.set_authorize(riot_auth)
            return await super().fetch_match_history(
                puuid=puuid,
                queue=queue,
                start=start,
                end=end,
                with_details=with_details,
            )

    # party

    @_authorize_required
    async def fetch_party_player(self, *, riot_auth: Optional[RiotAuth] = None) -> PartyPlayer:
        async with self.lock:
            if riot_auth is not None:
                await self.set_authorize(riot_auth)
            data = await self.http.get_party_player()
            return PartyPlayer(client=self, data=data)

    @_authorize_required
    async def fetch_party(self, party_id: str, *, riot_auth: Optional[RiotAuth] = None) -> Party:
        async with self.lock:
            if riot_auth is not None:
                await self.set_authorize(riot_auth)
            data = await self.http.get_party(party_id=party_id)
            return Party(client=self, data=data)

    @_authorize_required
    async def party_invite_by_riot_id(
        self,
        party_id: str,
        game_name: str,
        tag_line: str,
        *,
        riot_auth: Optional[RiotAuth] = None,
    ) -> Party:
        async with self.lock:
            if riot_auth is not None:
                await self.set_authorize(riot_auth)
            data = await self.http.post_party_invite_by_display_name(party_id, game_name, tag_line)
            return Party(client=self, data=data)
