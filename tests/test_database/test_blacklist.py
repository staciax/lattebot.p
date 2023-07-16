from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from core.database.errors import BlacklistAlreadyExists, BlacklistDoesNotExist

from .conftest import DatabaseSetup
from .mock_data import BLACKLIST_DATA

if TYPE_CHECKING:
    from core.database import DatabaseConnection


class TestBlackList(DatabaseSetup):
    @pytest.mark.asyncio
    async def test_add_blacklist(self, db: DatabaseConnection) -> None:
        for data in BLACKLIST_DATA:
            blacklist = await db.add_blacklist(**data)
            assert blacklist is not None

        try:
            await db.add_blacklist(3)
        except Exception as e:
            assert isinstance(e, BlacklistAlreadyExists)

    @pytest.mark.asyncio
    async def test_get_blacklist(self, db: DatabaseConnection) -> None:
        blacklist = await db.get_blacklist(1)
        assert blacklist is not None
        assert blacklist.id == 1
        assert blacklist.reason == 'test'

        blacklist = await db.get_blacklist(2)
        assert blacklist is not None
        assert blacklist.id == 2
        assert blacklist.reason == 'test'

    @pytest.mark.asyncio
    async def test_get_blacklists(self, db: DatabaseConnection) -> None:
        async for blacklist in db.get_blacklists():
            assert blacklist is not None
            assert blacklist.reason == 'test'

    @pytest.mark.asyncio
    async def test_remove_blacklist(self, db: DatabaseConnection) -> None:
        await db.remove_blacklist(1)
        blacklist = await db.get_blacklist(1)
        assert blacklist is None

        await db.remove_blacklist(2)
        blacklist = await db.get_blacklist(2)
        assert blacklist is None

        try:
            await db.remove_blacklist(0)
        except Exception as e:
            assert isinstance(e, BlacklistDoesNotExist)

    @pytest.mark.asyncio
    async def test_blacklist_is_deleted(self, db: DatabaseConnection) -> None:
        assert await db.get_blacklist(1) is None
        assert await db.get_blacklist(2) is None
        assert await db.get_blacklist(3) is not None
