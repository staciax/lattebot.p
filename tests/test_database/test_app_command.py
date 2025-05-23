from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .conftest import DatabaseSetup
from .mock_data import APP_COMMAND_DATA

if TYPE_CHECKING:
    from core.database import DatabaseConnection


class TestCommand(DatabaseSetup):
    @pytest.mark.asyncio
    async def test_add_command(self, db: DatabaseConnection) -> None:
        for data in APP_COMMAND_DATA:
            command = await db.add_app_command(**data)
            assert command is not None

    @pytest.mark.asyncio
    async def test_get_commands(self, db: DatabaseConnection) -> None:
        commands = []
        async for command in db.fetch_app_commands():
            assert command is not None
            commands.append(command)
        assert len(commands) == len(APP_COMMAND_DATA)

    @pytest.mark.asyncio
    async def test_get_commands_by_name(self, db: DatabaseConnection) -> None:
        commands = []
        async for command in db.fetch_app_commands_by_name(name='test 1'):
            assert command is not None
            commands.append(command)
        assert len(commands) == 1
