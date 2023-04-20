from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Tuple

from valorantx2 import ClientUser

if TYPE_CHECKING:
    from valorantx2.valorant_api.models import PlayerCard

    from ..types.account_henrikdev import Account as AccountPayload
    from ..valorant_api_cache import Cache

# fmt: off
__all__: Tuple[str, ...] = (
    'PartialUser',
)
# fmt: on


class PartialUser(ClientUser):
    account_level: int
    player_card: Optional[PlayerCard]
    _last_update: str
    _last_update_raw: int

    def __init__(self, *, state: Cache, data: AccountPayload) -> None:
        self._update(state, data)

    def __repr__(self) -> str:
        return f'<PartialUser puuid={self.puuid!r} name={self.name!r} tag={self.tag!r}>'

    def _update(self, state: Cache, data: AccountPayload) -> None:
        self.puuid: str = data['puuid']
        self._username = data.get('name')
        self._tagline = data['tag']
        self._region = data.get('region')
        self.account_level: int = data.get('account_level', 0)
        self.player_card: Optional[PlayerCard] = state.get_player_card(data.get('card', {}).get('id'))
        self._last_update: str = data.get('last_update')
        self._last_update_raw: int = data.get('last_update_raw')

    @property
    def name(self) -> Optional[str]:
        """:class:`str`: The account's name."""
        return self._username

    @property
    def tag(self) -> Optional[str]:
        """:class:`str`: The account's tag."""
        return self._tagline

    @property
    def riot_id(self) -> str:
        """:class:`str`: The account's riot id."""
        return f'{self.name}#{self.tag}'

    @property
    def last_update(self) -> datetime:
        """:class:`datetime.datetime`: The last time the account was updated."""
        return datetime.fromtimestamp(self._last_update_raw / 1000)


# class Player(valorantx.Player):
#     @classmethod
#     def from_partial_account(cls, client: Client, account: PartialAccount) -> Self:
#         payload = {
#             'puuid': str(account.puuid),
#             'username': account.name,
#             'tagline': account.tag,
#             'region': account.region,
#         }
#         return cls(client=client, data=payload)
