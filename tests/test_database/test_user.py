from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from core.database.errors import UserAlreadyExists, UserDoesNotExist

from .conftest import DatabaseSetup
from .mock_data import USER_DATA

if TYPE_CHECKING:
    from core.database import DatabaseConnection


class TestUser(DatabaseSetup):
    @pytest.mark.asyncio
    async def test_add_user(self, db: DatabaseConnection) -> None:
        for data in USER_DATA:
            user_id = data.pop('id')
            user = await db.add_user(user_id, **data)
            assert user is not None

        try:
            await db.add_user(3)
        except Exception as e:
            assert isinstance(e, UserAlreadyExists)

    @pytest.mark.asyncio
    async def test_get_user(self, db: DatabaseConnection) -> None:
        user = await db.fetch_user(1)
        assert user is not None
        assert user.id == 1

        user = await db.fetch_user(2)
        assert user is not None
        assert user.id == 2

    @pytest.mark.asyncio
    async def test_get_users(self, db: DatabaseConnection) -> None:
        async for user in db.fetch_users():
            assert user is not None

    @pytest.mark.asyncio
    async def test_update_user(self, db: DatabaseConnection) -> None:
        await db.update_user(1)
        user = await db.fetch_user(1)
        assert user is not None
        assert user.id == 1

        await db.update_user(2)
        user = await db.fetch_user(2)
        assert user is not None
        assert user.id == 2

        try:
            await db.update_user(0)
        except Exception as e:
            assert isinstance(e, UserDoesNotExist)

    @pytest.mark.asyncio
    async def test_remove_user(self, db: DatabaseConnection) -> None:
        await db.remove_user(1)
        user = await db.fetch_user(1)
        assert user is None

        await db.remove_user(2)
        user = await db.fetch_user(2)
        assert user is None

        try:
            await db.remove_user(0)
        except Exception as e:
            assert isinstance(e, UserDoesNotExist)

    @pytest.mark.asyncio
    async def test_user_is_deleted(self, db: DatabaseConnection) -> None:
        assert await db.fetch_user(1) is None
        assert await db.fetch_user(2) is None
        assert await db.fetch_user(3) is not None
