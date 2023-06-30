from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from core.database.connection import DatabaseConnection as _DatabaseConnection
from core.database.models.blacklist import BlackList
from core.database.models.notification_settings import NotificationSettings
from core.database.models.riot_account import RiotAccount
from core.database.models.user import User

# fmt: off
__all__ = (
    'DatabaseConnection',
)
# fmt: on


class DatabaseConnection(_DatabaseConnection):
    def __init__(self, uri: str, echo: bool = False) -> None:
        super().__init__(uri, echo=echo)
        self._log = logging.getLogger(__name__)
        self._users: Dict[int, User] = {}  # TODO: key to string
        self._blacklist: Dict[int, BlackList] = {}
        self.lock = asyncio.Lock()
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
        self._log.debug('stored user %d in cache', user.id)

    async def _refresh_user_by_id(self, id: int, /) -> None:
        async with self.lock:
            try:
                del self._users[id]
            except KeyError:
                pass
            else:
                await self.get_user(id)
                self._log.debug('refreshed user %d in cache', id)

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
        /,
        *,
        locale: Optional[str] = None,
        main_account_id: Optional[int] = None,
    ) -> None:
        await super().update_user(id, locale=locale, main_account_id=main_account_id)
        # refresh user cache
        self.loop.create_task(self._refresh_user_by_id(id))

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
        self._log.debug('stored blacklist %d in cache', blacklist.id)

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
        incognito: bool = False,
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
            incognito=incognito,
            notify=notify,
        )

        # refresh user cache
        self.loop.create_task(self._refresh_user_by_id(owner_id))

        return riot_account

    async def delete_riot_account(self, puuid: str, owner_id: int) -> None:
        await super().delete_riot_account(puuid, owner_id)

        # refresh user cache
        self.loop.create_task(self._refresh_user_by_id(owner_id))

    async def delete_all_riot_accounts(self, owner_id: int) -> None:
        await super().delete_all_riot_accounts(owner_id)

        # refresh user cache
        self.loop.create_task(self._refresh_user_by_id(owner_id))

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
        incognito: Optional[bool] = None,
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
            incognito=incognito,
            notify=notify,
        )
        if update:
            # refresh user cache
            self.loop.create_task(self._refresh_user_by_id(owner_id))

        return update

    # notification settings

    async def create_notification_settings(
        self,
        owner_id: int,
        *,
        channel_id: int,
        mode: int,
        enabled: bool,
    ) -> NotificationSettings:
        notification_settings = await super().create_notification_settings(
            owner_id,
            channel_id=channel_id,
            mode=mode,
            enabled=enabled,
        )

        # refresh user cache
        self.loop.create_task(self._refresh_user_by_id(owner_id))

        return notification_settings

    async def update_notification_settings(
        self,
        owner_id: int,
        *,
        channel_id: Optional[int] = None,
        mode: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[NotificationSettings]:
        notification_settings = await super().update_notification_settings(
            owner_id,
            channel_id=channel_id,
            mode=mode,
            enabled=enabled,
        )
        if notification_settings:
            # refresh user cache
            self.loop.create_task(self._refresh_user_by_id(owner_id))

        return notification_settings

    async def delete_notification_settings(self, owner_id: int, /) -> bool:
        delete = await super().delete_notification_settings(owner_id)
        if delete:
            # refresh user cache
            self.loop.create_task(self._refresh_user_by_id(owner_id))
        return delete
