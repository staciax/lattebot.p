from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional

from core.utils.database.connection import DatabaseConnection as BaseDatabaseConnection
from core.utils.database.models.blacklist import BlackList
from core.utils.database.models.riot_account import RiotAccount
from core.utils.database.models.user import User

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

    async def initialize(self, drop_table: bool = False) -> None:
        await super().initialize(drop_table)
        await self._cache_users()
        await self._cache_blacklist()
        self._log.info('cached %d users and %d blacklists', len(self._users), len(self._blacklist))

    async def _cache_users(self) -> None:
        async for user in super().get_users():
            self._users[user.id] = user
        self._log.info('cached %d users', len(self._users))

    async def _cache_blacklist(self) -> None:
        async for user in super().get_blacklists():
            self._blacklist[user.id] = user
        self._log.info('cached %d blacklists', len(self._blacklist))

    async def reload_cache(self) -> None:
        await self._cache_users()
        await self._cache_blacklist()

    @property
    def users(self) -> List[User]:
        return list(self._users.values())

    @property
    def blacklist(self) -> List[BlackList]:
        return list(self._blacklist.values())

    # user

    def _store_user(self, user: User) -> None:
        self._users[user.id] = user

    async def create_user(self, *, id: int, locale: Any = 'en_US') -> User:
        user = await super().create_user(id=id, locale=str(locale))
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

    async def get_or_create_user(self, *, id: int, locale: Any = 'en_US') -> User:
        user = await self.get_user(id)
        if user is None:
            user = await self.create_user(id=id, locale=locale)
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

        # delete from cache
        try:
            del self._users[id]
        except KeyError:
            pass

        self._log.info('deleted user %d from cache', id)

    # blacklist

    def _store_blacklist(self, blacklist: BlackList) -> None:
        self._blacklist[blacklist.id] = blacklist
        self._log.info('stored blacklist %d in cache', blacklist.id)

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
        else:
            self._log.info('deleted blacklist %d from cache', id)

    # riot account

    async def create_riot_account(
        self,
        *,
        puuid: str,
        game_name: Optional[str],
        tag_line: Optional[str],
        region: str,
        scope: str,
        token_type: str,
        expires_at: int,
        id_token: str,
        access_token: str,
        entitlements_token: str,
        owner_id: int,
    ) -> RiotAccount:
        riot_account = await super().create_riot_account(
            puuid=puuid,
            game_name=game_name,
            tag_line=tag_line,
            region=region,
            scope=scope,
            token_type=token_type,
            id_token=id_token,
            expires_at=expires_at,
            access_token=access_token,
            entitlements_token=entitlements_token,
            owner_id=owner_id,
        )

        # validate cache
        try:
            self._users.pop(owner_id)
        except KeyError:
            pass
        else:
            # user = self._users[owner_id]
            # for account in user.riot_accounts:
            #     if account.puuid == puuid:
            #         account = riot_account
            #         break
            # refresh user from database
            self._bot.loop.create_task(self.get_user(owner_id))

        return riot_account

    async def delete_riot_account(self, puuid: str, owner_id: int) -> None:
        await super().delete_riot_account(puuid, owner_id)

        # validate cache
        try:
            self._users.pop(owner_id)
        except KeyError:
            pass
        else:
            # refresh user from database
            self._bot.loop.create_task(self.get_user(owner_id))

    async def delete_all_riot_accounts(self, owner_id: int) -> None:
        await super().delete_all_riot_accounts(owner_id)

        # validate cache
        try:
            self._users.pop(owner_id)
        except KeyError:
            pass
        else:
            self._bot.loop.create_task(self.get_user(owner_id))
