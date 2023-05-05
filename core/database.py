from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncIterator, Dict, List, Optional

from core.utils.database import BlackList, DatabaseConnection as BaseDatabaseConnection, User

if TYPE_CHECKING:
    from core.bot import LatteMaid

__all__ = (
    'DatabaseConnection',
    'User',
    'BlackList',
)


class DatabaseConnection(BaseDatabaseConnection):
    def __init__(self, bot: LatteMaid, uri: str) -> None:
        super().__init__(uri)
        self._bot: LatteMaid = bot
        self._log = logging.getLogger(__name__)
        self._users: Dict[int, User] = {}
        self._blacklist: Dict[int, BlackList] = {}

    async def initialize(self, drop_table: bool = True) -> None:
        await super().initialize(drop_table)
        await self._cache_users()
        await self._cache_blacklist()
        self._log.info('cached %d users and %d blacklists', len(self._users), len(self._blacklist))

    async def _cache_users(self) -> None:
        async for user in self.get_users():
            self._users[user.id] = user

    async def _cache_blacklist(self) -> None:
        async for user in self.get_blacklists():
            self._blacklist[user.id] = user

    @property
    def users(self) -> List[User]:
        return list(self._users.values())

    @property
    def blacklist(self) -> List[BlackList]:
        return list(self._blacklist.values())

    # user overrides

    def _store_user(self, user: User) -> None:
        self._users[user.id] = user

    async def create_user(self, *, id: int, locale: str = 'en_US') -> User:
        user = await super().create_user(id=id, locale=locale)
        if user is not None and user.id not in self._users:
            self._store_user(user)
        return user

    async def get_user(self, id: int) -> Optional[User]:
        if id in self._users:
            return self._users[id]
        user = await super().get_user(id)
        if user is not None:
            self._store_user(user)
        return user

    async def get_users(self) -> AsyncIterator[User]:
        async for user in super().get_users():
            if user.id not in self._users:
                self._store_user(user)
            yield user

    async def update_user(self, id: int, locale: str) -> None:
        await super().update_user(id, locale)
        if id in self._users:
            self._users[id].locale = locale

    async def delete_user(self, id: int) -> None:
        await super().delete_user(id)
        try:
            del self._users[id]
        except KeyError:
            pass

    # blacklist overrides

    def _store_blacklist(self, blacklist: BlackList) -> None:
        self._blacklist[blacklist.id] = blacklist

    async def create_blacklist(self, *, id: int) -> BlackList:
        blacklist = await super().create_blacklist(id=id)
        if blacklist is not None and blacklist.id not in self._blacklist:
            self._store_blacklist(blacklist)
        return blacklist

    async def get_blacklist(self, id: int) -> Optional[BlackList]:
        if id in self._blacklist:
            return self._blacklist[id]
        blacklist = await super().get_blacklist(id)
        if blacklist is not None:
            self._store_blacklist(blacklist)
        return blacklist

    async def get_blacklists(self) -> AsyncIterator[BlackList]:
        async for blacklist in super().get_blacklists():
            if blacklist.id not in self._blacklist:
                self._store_blacklist(blacklist)
            yield blacklist

    async def delete_blacklist(self, id: int) -> None:
        await super().delete_blacklist(id)
        try:
            del self._blacklist[id]
        except KeyError:
            pass
