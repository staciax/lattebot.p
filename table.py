import asyncio
import logging
import os

from dotenv import load_dotenv

from core.database import DatabaseConnection

load_dotenv()

DATABASE_URL_TEST = os.getenv('DATABASE_URL_TEST')
if DATABASE_URL_TEST is None:
    raise EnvironmentError('DATABASE_URL_TEST is not set')

# PASSWORD_REGEX = re.compile(r'^(?=.*[a-zA-Z\d])(?=.*[a-zA-Z\d\s:]).{8,128}$')
# PASSWORD_REGEX = re.compile(r'^(?=.*[a-zA-Z\d])(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{8,128}$')


async def main():
    db = DatabaseConnection(DATABASE_URL_TEST, echo=False)
    await db.initialize(drop_table=True)

    user_id = 4
    user = await db.add_user(user_id)
    assert user is not None
    assert user.id == user_id

    bl = await db.add_blacklist(user.id, reason='test')
    assert bl.object_id == user.id
    assert bl.reason == 'test'

    user = await db.fetch_user(user.id)
    assert user is not None
    assert user.is_blacklisted()

    await db.remove_blacklist(user.id)
    user = await db.fetch_user(user.id)
    assert user is not None
    assert not user.is_blacklisted()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
