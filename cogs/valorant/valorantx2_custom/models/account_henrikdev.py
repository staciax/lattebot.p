from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from valorantx2.valorant_api.models import PlayerCard

    from ..types.account_henrikdev import Account as AccountPayload
    from ..valorant_api_cache import Cache

# fmt: off
__all__: Tuple[str, ...] = (
    'PartialAccount',
)
# fmt: on


class PartialAccount:
    puuid: str
    region: str
    account_level: int
    name: str
    tag: str
    player_card: Optional[PlayerCard]
    _last_update: str
    _last_update_raw: int

    __slots__ = (
        'puuid',
        'region',
        'account_level',
        'name',
        'tag',
        'player_card',
        '_last_update',
        '_last_update_raw',
    )

    def __init__(self, state: Cache, data: AccountPayload) -> None:
        self.player_card: Optional[PlayerCard] = None
        self._update(state, data)

    def __repr__(self) -> str:
        return f'<PartialAccount puuid={self.puuid!r} name={self.name!r} tag={self.tag!r}>'

    @property
    def riot_id(self) -> str:
        """:class:`str`: The account's riot id."""
        return f'{self.name}#{self.tag}'

    @property
    def last_update(self) -> datetime:
        """:class:`datetime.datetime`: The last time the account was updated."""
        return datetime.fromtimestamp(self._last_update_raw / 1000)

    def _update(self, state: Cache, data: AccountPayload) -> None:
        self.puuid: str = data['puuid']
        self.region: str = data['region']
        self.account_level: int = data['account_level']
        self.name: str = data['name']
        self.tag: str = data['tag']
        self.player_card: Optional[PlayerCard] = state.get_player_card(data['card']['id'])
        self._last_update: str = data['last_update']
        self._last_update_raw: int = data['last_update_raw']


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
