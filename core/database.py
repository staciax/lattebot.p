from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from core.utils.database.connection import DatabaseConnection as _DatabaseConnection
from core.utils.database.models.blacklist import BlackList
from core.utils.database.models.riot_account import RiotAccount
from core.utils.database.models.user import User

__all__ = (
    'DatabaseConnection',
    'User',
    'BlackList',
)


class DatabaseConnection(_DatabaseConnection):
    def __init__(self, uri: str) -> None:
        super().__init__(uri, echo=False)
        self._log = logging.getLogger(__name__)
        self._users: Dict[int, User] = {}  # TODO: key to string
        self._blacklist: Dict[int, BlackList] = {}
        self.loop = asyncio.get_running_loop()
        self.loop.create_task(self.initialize())

    async def initialize(self, drop_table: bool = False) -> None:
        await super().initialize(drop_table)
        await self._cache_users()
        await self._cache_blacklist()
        self._log.info('initialized database')

    async def _cache_users(self) -> None:
        async for user in super().get_users():
            self._users[user.id] = user
        self._log.debug('cached %d users', len(self._users))

    async def _cache_blacklist(self) -> None:
        async for user in super().get_blacklists():
            self._blacklist[user.id] = user
        self._log.debug('cached %d blacklists', len(self._blacklist))

    async def reload_cache(self) -> None:
        await self._cache_users()
        await self._cache_blacklist()
        self._log.info('reloaded cache')

    @property
    def users(self) -> List[User]:
        return list(self._users.values())

    @property
    def blacklist(self) -> List[BlackList]:
        return list(self._blacklist.values())

    # user

    def _store_user(self, user: User) -> None:
        self._users[user.id] = user

    async def create_user(self, id: int, *, locale: Any = 'en-US') -> User:
        user = await super().create_user(id, locale=str(locale))
        if user is not None and user.id not in self._users:
            self._store_user(user)
        return user

    async def get_user(self, id: int, /) -> Optional[User]:
        if id in self._users:
            return self._users[id]
        user = await super().get_user(id)
        if user is not None:
            self._store_user(user)
        return user

    async def get_or_create_user(self, id: int, /, locale: Any = 'en-US') -> User:
        user = await self.get_user(id)
        if user is None:
            user = await self.create_user(id, locale=locale)
        return user

    async def get_users(self) -> AsyncIterator[User]:
        async for user in super().get_users():
            if user.id not in self._users:
                self._store_user(user)
            yield user

    async def update_user(
        self,
        id: int,
        *,
        locale: Optional[str] = None,
        main_account_id: Optional[int] = None,
    ) -> None:
        await super().update_user(id, locale=locale, main_account_id=main_account_id)
        if id in self._users:
            if locale is not None:
                self._users[id].locale = locale
            if main_account_id is not None:
                self._users[id].main_riot_account_id = main_account_id

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

    async def create_blacklist(self, id: int, /) -> BlackList:
        blacklist = await super().create_blacklist(id=id)
        if blacklist is not None and blacklist.id not in self._blacklist:
            self._store_blacklist(blacklist)
        return blacklist

    async def get_blacklist(self, id: int, /) -> Optional[BlackList]:
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
        owner_id: int,
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
        ssid: str,
        notify: bool = True,
    ) -> RiotAccount:
        riot_account = await super().create_riot_account(
            owner_id=owner_id,
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
            ssid=ssid,
            notify=notify,
        )

        # validate cache
        try:
            self._users.pop(owner_id)
        except KeyError:
            pass
        else:
            # refresh user from database
            self.loop.create_task(self.get_user(owner_id))

        return riot_account

    async def delete_riot_account(self, puuid: str, owner_id: int) -> None:
        await super().delete_riot_account(puuid, owner_id)

        # validate cache
        try:
            self._users.pop(owner_id)
        except KeyError:
            pass

    async def delete_all_riot_accounts(self, owner_id: int) -> None:
        await super().delete_all_riot_accounts(owner_id)

        # validate cache
        try:
            self._users.pop(owner_id)
        except KeyError:
            pass

    async def update_riot_account(
        self,
        puuid: str,
        owner_id: int,
        *,
        game_name: Optional[str] = None,
        tag_line: Optional[str] = None,
        region: Optional[str] = None,
        scope: Optional[str] = None,
        token_type: Optional[str] = None,
        expires_at: Optional[int] = None,
        id_token: Optional[str] = None,
        access_token: Optional[str] = None,
        entitlements_token: Optional[str] = None,
        ssid: Optional[str] = None,
        notify: Optional[bool] = None,
    ) -> bool:
        update = await super().update_riot_account(
            puuid,
            owner_id,
            game_name=game_name,
            tag_line=tag_line,
            region=region,
            scope=scope,
            token_type=token_type,
            expires_at=expires_at,
            id_token=id_token,
            access_token=access_token,
            entitlements_token=entitlements_token,
            ssid=ssid,
            notify=notify,
        )
        if update:
            # validate cache
            try:
                self._users.pop(owner_id)
            except KeyError:
                pass
            else:
                # refresh user from database
                self.loop.create_task(self.get_user(owner_id))

        return update
