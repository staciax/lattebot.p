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
from .models import PartialUser, PatchNote
from .valorant_api_client import Client as ValorantAPIClient

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

    async def fetch_patch_note_from_site(self, url: str) -> PatchNote:
        # TODO: doc
        text = await self.http.text_from_url(url)
        return PatchNote.from_text(self, text)

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
        return PartialUser(state=self.valorant_api._cache, data=data['data'])
