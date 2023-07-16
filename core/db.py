from __future__ import annotations

import asyncio
import logging

from core.database.connection import DatabaseConnection as _DatabaseConnection
from core.database.models.blacklist import BlackList

# fmt: off
__all__ = (
    'DatabaseConnection',
)
# fmt: on


class DatabaseConnection(_DatabaseConnection):
    def __init__(self, uri: str, echo: bool = False) -> None:
        super().__init__(uri, echo=echo)
        self._log = logging.getLogger(__name__)
        self._blacklist: dict[int, BlackList] = {}
        self.lock = asyncio.Lock()
        self.loop = asyncio.get_running_loop()
        self.loop.create_task(self.initialize())

    async def initialize(self, drop_table: bool = False) -> None:
        await super().initialize(drop_table)
        await self._cache_blacklist()
        self._log.info('initialized database')

    async def _cache_blacklist(self) -> None:
        async for user in super().get_blacklists():
            self._blacklist[user.id] = user
        self._log.debug('cached %d blacklists', len(self._blacklist))

    @property
    def blacklist(self) -> list[BlackList]:
        return list(self._blacklist.values())

    def _store_blacklist(self, blacklist: BlackList) -> None:
        self._blacklist[blacklist.id] = blacklist
        self._log.debug('stored blacklist %d in cache', blacklist.id)

    async def add_blacklist(self, id: int, /) -> BlackList:
        blacklist = await super().add_blacklist(id=id)
        if blacklist is not None and blacklist.id not in self._blacklist:
            self._store_blacklist(blacklist)
        return blacklist

    async def delete_blacklist(self, id: int) -> None:
        await super().delete_blacklist(id)
        try:
            del self._blacklist[id]
        except KeyError:
            pass
        else:
            self._log.info('deleted blacklist %d from cache', id)
