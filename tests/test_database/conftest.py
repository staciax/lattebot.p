import asyncio
import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from core.database.connection import DatabaseConnection

load_dotenv()

DATABASE_URL_TEST = os.getenv('DATABASE_URL_TEST')
if DATABASE_URL_TEST is None:
    raise EnvironmentError('DATABASE_URL_TEST is not set')


@pytest.fixture(scope='session')
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope='class')
async def db():
    _db = DatabaseConnection(DATABASE_URL_TEST)
    yield _db
    await _db.close()


class DatabaseSetup:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def setup(self, db: DatabaseConnection) -> None:
        await db.initialize(drop_table=True)
