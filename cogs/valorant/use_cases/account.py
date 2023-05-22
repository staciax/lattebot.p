from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..valorantx2 import RiotAuth

# import asyncio

if TYPE_CHECKING:
    from ..valorantx2 import Client

# TODO: dirname ui to usecase หรือ อะไรสักอย่าง


class User:
    def __init__(self, user_id: int, riot_auths: List[RiotAuth] = []) -> None:
        self.user_id: int = user_id
        self.riot_auths: Dict[str, RiotAuth] = {riot_auth.puuid: riot_auth for riot_auth in riot_auths}

    def insert_riot_auth(self, riot_auth: RiotAuth) -> None:
        self.riot_auths[riot_auth.puuid] = riot_auth

    def remove_riot_auth(self, puuid: str) -> None:
        try:
            self.riot_auths.pop(puuid)
        except KeyError:
            pass

    def get_riot_auth(self, puuid: str) -> Optional[RiotAuth]:
        return self.riot_auths.get(puuid)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            'user_id': self.user_id,
            'riot_auths': [riot_auth.to_dict() for riot_auth in self.riot_auths.values()],
        }
        return payload

    @classmethod
    def from_orm(cls, data: Dict[str, Any]) -> User:
        ...
        # return cls(
        #     data['user_id'],
        #     [RiotAuth.from_dict(riot_auth) for riot_auth in data['riot_auths']],
        # )

    # def __repr__(self) -> str:
    #     return f'<Account puuid={self.puuid!r} riot_id={self.riot_id!r}>'

    # def __eq__(self, object: object) -> bool:
    #     return isinstance(object, Account) and self.puuid == object.puuid

    # def __ne__(self, object: object) -> bool:
    #     return not self.__eq__(object)

    # def __hash__(self) -> int:
    #     return hash(self.puuid)

    # @property
    # def puuid(self) -> str:
    #     return self.riot_auth.puuid

    # @property
    # def riot_id(self) -> str:
    #     return self.riot_auth.display_name

    # @classmethod
    # def from_data(cls, data: Dict[str, Any]) -> Account:
    #     riot_auth = RiotAuth()  # TODO: classmethod RiotAuth.from_data(data)
    #     riot_auth.from_data(data)
    #     return cls(riot_auth)


class AccountManager:
    def __init__(self, client: Client) -> None:
        self.client: Client = client
        # self._riot_accounts: Dict[str, Account] = {}
        # self.current_account: Account = None

    # def switch_account(self, puuid: str) -> None:
    #     account = self._riot_accounts.get(puuid)
    #     if account is None:
    #         raise ValueError("Account does not exist")
    #     self.current_account = account

    # async def fetch_store_front(self) -> None:
    #     await self.current_account.fetch_store_front()

    # async def fetch_contracts(self) -> None:
    #     await self.current_account.fetch_contracts()

    # async def fetch_loadouts(self) -> None:
    #     await self.current_account.fetch_loadouts()
