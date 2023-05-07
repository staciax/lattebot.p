import asyncio
from typing import Any, Coroutine, List, Optional, TypeVar

import valorantx2 as valorantx
from async_lru import alru_cache
from valorantx2 import Locale
from valorantx2.auth import RiotAuth
from valorantx2.client import _loop  # _authorize_required
from valorantx2.enums import try_enum
from valorantx2.models.store import StoreFront
from valorantx2.models.user import ClientUser
from valorantx2.utils import MISSING
from valorantx2.valorant_api.models.version import Version as ValorantAPIVersion

from .http import HTTPClient
from .models import PartialUser, PatchNoteScraper
from .valorant_api_client import Client as ValorantAPIClient

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

    async def fetch_storefront(self, riot_auth: Optional[RiotAuth] = None) -> StoreFront:
        async with self._lock:
            data = await self.http.get_store_storefront()
            return StoreFront(self.valorant_api.cache, data)
