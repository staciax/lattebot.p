from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from core.utils.database.errors import UserAlreadyExists, UserDoesNotExist

from .conftest import DatabaseSetup
from .mock_data import USER_DATA

if TYPE_CHECKING:
    from core.utils.database import DatabaseConnection


class TestUser(DatabaseSetup):
    @pytest.mark.asyncio
    async def test_create_user(self, db: DatabaseConnection) -> None:
        for data in USER_DATA:
            user = await db.create_user(**data)
            assert user is not None

        try:
            await db.create_user(id=3)
        except Exception as e:
            assert isinstance(e, UserAlreadyExists)

    @pytest.mark.asyncio
    async def test_get_user(self, db: DatabaseConnection) -> None:
        user = await db.get_user(id=1)
        assert user is not None
        assert user.id == 1
        assert user.locale == 'en_US'

        user = await db.get_user(id=2)
        assert user is not None
        assert user.id == 2
        assert user.locale == 'en_GB'

    @pytest.mark.asyncio
    async def test_get_users(self, db: DatabaseConnection) -> None:
        async for user in db.get_users():
            assert user is not None
            if user.id == 1:
                assert user.locale == 'en_US'
            elif user.id == 2:
                assert user.locale == 'en_GB'
            elif user.id == 3:
                assert user.locale == 'th_TH'

    @pytest.mark.asyncio
    async def test_update_user(self, db: DatabaseConnection) -> None:
        await db.update_user(id=1, locale='en_GB')
        user = await db.get_user(id=1)
        assert user is not None
        assert user.id == 1
        assert user.locale == 'en_GB'

        await db.update_user(id=2, locale='en_US')
        user = await db.get_user(id=2)
        assert user is not None
        assert user.id == 2
        assert user.locale == 'en_US'

        try:
            await db.update_user(id=0, locale='en_US')
        except Exception as e:
            assert isinstance(e, UserDoesNotExist)

    @pytest.mark.asyncio
    async def test_delete_user(self, db: DatabaseConnection) -> None:
        await db.delete_user(id=1)
        user = await db.get_user(id=1)
        assert user is None

        await db.delete_user(id=2)
        user = await db.get_user(id=2)
        assert user is None

        try:
            await db.delete_user(id=0)
        except Exception as e:
            assert isinstance(e, UserDoesNotExist)

    @pytest.mark.asyncio
    async def test_user_is_deleted(self, db: DatabaseConnection) -> None:
        assert await db.get_user(id=1) is None
        assert await db.get_user(id=2) is None
        assert await db.get_user(id=3) is not None
