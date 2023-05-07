import asyncio
import os

from dotenv import load_dotenv

from core.database import DatabaseConnection

load_dotenv()

DATABASE_URI_TEST = os.getenv('DATABASE_URI_TEST')
if DATABASE_URI_TEST is None:
    raise EnvironmentError('DATABASE_URI_TEST is not set')


db = DatabaseConnection(None, DATABASE_URI_TEST)


async def main():
    await db.initialize(drop_table=True)


if __name__ == "__main__":
    asyncio.run(main())
