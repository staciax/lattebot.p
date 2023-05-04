# import sqlalchemy
import asyncio
import datetime
import logging
from typing import AsyncIterator, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .errors import BlacklistAlreadyExists, BlacklistDoesNotExist, UserAlreadyExists, UserDoesNotExist
from .models.base import Base
from .models.blacklist import BlackList
from .models.command import Command
from .models.user import User

# fmt: off
__all__ = (
    'DatabaseConnection',
)
# fmt: on


class DatabaseConnection:
    _async_session: async_sessionmaker[AsyncSession]
    _async_engine: AsyncEngine

    def __init__(self, uri: str, echo: bool = False) -> None:
        self.__uri: str = uri
        self._echo: bool = echo
        self._ready: asyncio.Event = asyncio.Event()
        self._log: logging.Logger = logging.getLogger(__name__)
        self._is_closed: bool = False

    def is_closed(self) -> bool:
        return self._is_closed

    async def initialize(self, drop_table: bool = True) -> None:
        self._async_engine = create_async_engine(self.__uri, echo=self._echo)
        self._async_session = async_sessionmaker(self._async_engine, expire_on_commit=False, autoflush=False)
        await self._create_tables(drop=drop_table)
        self._ready.set()
        del self.__uri  # delete uri to prevent accidental use
        self._log.info('database connection initialized')

    async def _create_tables(self, drop: bool = False) -> None:
        self._log.info('creating tables . . .')
        async with self._async_engine.begin() as engine:
            if drop:
                await engine.run_sync(Base.metadata.drop_all)
            await engine.run_sync(Base.metadata.create_all)
        self._log.info('tables created !')

    async def close(self) -> None:
        self._is_closed = True
        await self._async_engine.dispose()
        self._async_session.configure(bind=None)
        self._log.info('database connection closed')

    def is_ready(self) -> bool:
        return self._ready.is_set()

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    async def get_session(self) -> AsyncSession:
        return self._async_session()

    # user

    async def create_user(self, *, id: int, locale: str = 'en_US') -> User:
        async with self._async_session() as session:
            exist_user = await User.read_by_id(session, id)
            if exist_user:
                raise UserAlreadyExists(f"user with id {id!r} already exists")
            user = await User.create(session=session, id=id, locale=locale)
            await session.commit()
            self._log.info(f'created user with id {id!r}')
            return user

    async def get_user(self, id: int) -> Optional[User]:
        async with self._async_session() as session:
            user = await User.read_by_id(session, id)
            return user

    async def get_users(self) -> AsyncIterator[User]:
        async with self._async_session() as session:
            async for user in User.read_all(session):
                yield user

    async def update_user(self, id: int, locale: str) -> None:
        async with self._async_session() as session:
            user = await User.read_by_id(session, id)
            if not user:
                raise UserDoesNotExist(f"user with id {id!r} does not exist")
            await user.update(session, locale)
            await session.commit()
            self._log.info(f'updated user with id {id!r} to locale {locale!r}')

    async def delete_user(self, id: int) -> None:
        async with self._async_session() as session:
            user = await User.read_by_id(session, id)
            if not user:
                raise UserDoesNotExist(f"user with id {id!r} does not exist")
            await User.delete(session, user)
            await session.commit()
            self._log.info(f'deleted user with id {id!r}')

    # blacklist

    async def create_blacklist(self, *, id: int, reason: Optional[str] = None) -> BlackList:
        async with self._async_session() as session:
            exist_blacklist = await BlackList.read_by_id(session, id)
            if exist_blacklist:
                raise BlacklistAlreadyExists(f"blacklist with id {id!r} already exists")
            blacklist = await BlackList.create(session=session, id=id, reason=reason)
            await session.commit()
            self._log.info(f'created blacklist with id {id!r}')
            return blacklist

    async def get_blacklist(self, id: int) -> Optional[BlackList]:
        async with self._async_session() as session:
            stmt = select(BlackList).where(BlackList.id == id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_blacklists(self) -> AsyncIterator[BlackList]:
        async with self._async_session() as session:
            async for blacklist in BlackList.read_all(session):
                yield blacklist

    async def delete_blacklist(self, id: int) -> None:
        async with self._async_session() as session:
            blacklist = await BlackList.read_by_id(session, id)
            if not blacklist:
                raise BlacklistDoesNotExist(f"blacklist with id {id!r} does not exist")
            await BlackList.delete(session, blacklist)
            await session.commit()
            self._log.info(f'deleted blacklist with id {id!r}')

    # command

    async def create_command(
        self,
        guild: int,
        channel: int,
        author: int,
        used: datetime.datetime,
        prefix: str,
        command: str,
        failed: bool,
        app_command: bool,
    ) -> Command:
        async with self._async_session() as session:
            cmd = await Command.create(
                session=session,
                guild=guild,
                channel=channel,
                author=author,
                used=used,
                prefix=prefix,
                command=command,
                failed=failed,
                app_command=app_command,
            )
            await session.commit()
            self._log.info(f'created command with id {command!r}')
            return cmd

    async def get_commands(self) -> AsyncIterator[Command]:
        async with self._async_session() as session:
            async for cmd in Command.read_all(session):
                yield cmd

    async def get_commands_by_name(self, name: str) -> AsyncIterator[Command]:
        async with self._async_session() as session:
            async for cmd in Command.read_all_by_name(session, name):
                yield cmd
