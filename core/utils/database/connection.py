# import sqlalchemy
import asyncio
import datetime
import logging
from typing import AsyncIterator, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .errors import (
    BlacklistAlreadyExists,
    BlacklistDoesNotExist,
    RiotAccountAlreadyExists,
    RiotAccountDoesNotExist,
    UserAlreadyExists,
    UserDoesNotExist,
)
from .models.app_command import AppCommand
from .models.base import Base
from .models.blacklist import BlackList
from .models.riot_account import RiotAccount
from .models.user import User

# fmt: off
__all__ = (
    'DatabaseConnection',
)
# fmt: on


class DatabaseConnection:
    _async_session: async_sessionmaker[AsyncSession]
    _async_engine: AsyncEngine

    def __init__(self, uri: str, *, echo: bool = False) -> None:
        self.__uri: str = uri
        self._echo: bool = echo
        self._ready: asyncio.Event = asyncio.Event()
        self._log: logging.Logger = logging.getLogger(__name__)
        self._is_closed: bool = False

    def is_closed(self) -> bool:
        return self._is_closed

    async def initialize(self, drop_table: bool = False) -> None:
        self._async_engine = create_async_engine(self.__uri, echo=self._echo)
        self._async_session = async_sessionmaker(self._async_engine, expire_on_commit=False, autoflush=False)
        await self._create_tables(drop=drop_table)
        self._ready.set()
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

    async def create_user(self, id: int, *, locale: str = 'en-US') -> User:
        async with self._async_session() as session:
            exist_user = await User.read_by_id(session, id)
            if exist_user:
                raise UserAlreadyExists(f"user with id {id!r} already exists")
            user = await User.create(session=session, id=id, locale=locale)
            await session.commit()
            self._log.info(f'created user with id {id!r}')
            return user

    async def get_user(self, id: int, /) -> Optional[User]:
        async with self._async_session() as session:
            user = await User.read_by_id(session, id)
            return user

    async def get_users(self) -> AsyncIterator[User]:
        async with self._async_session() as session:
            async for user in User.read_all(session):
                yield user

    async def update_user(self, id: int, *, locale: str) -> bool:
        async with self._async_session() as session:
            user = await User.read_by_id(session, id)
            if not user:
                raise UserDoesNotExist(f"user with id {id!r} does not exist")
            try:
                await user.update(session, locale)
            except SQLAlchemyError as e:
                await session.rollback()
                self._log.error(f'failed to update user with id {id!r} due to {e!r}')
                return False
            else:
                await session.commit()
                self._log.info(f'updated user with id {id!r} to locale {locale!r}')
                return True

    async def delete_user(self, id: int, /) -> bool:
        async with self._async_session() as session:
            user = await User.read_by_id(session, id)
            if not user:
                raise UserDoesNotExist(f"user with id {id!r} does not exist")
            try:
                await User.delete(session, user)
            except SQLAlchemyError as e:
                await session.rollback()
                self._log.error(f'failed to delete user with id {id!r} due to {e!r}')
                return False
            else:
                await session.commit()
                self._log.info(f'deleted user with id {id!r}')
                return True

    # blacklist

    async def create_blacklist(self, id: int, *, reason: Optional[str] = None) -> BlackList:
        async with self._async_session() as session:
            exist_blacklist = await BlackList.read_by_id(session, id)
            if exist_blacklist:
                raise BlacklistAlreadyExists(f"blacklist with id {id!r} already exists")
            blacklist = await BlackList.create(session=session, id=id, reason=reason)
            await session.commit()
            self._log.info(f'created blacklist with id {id!r}')
            return blacklist

    async def get_blacklist(self, id: int, /) -> Optional[BlackList]:
        async with self._async_session() as session:
            stmt = select(BlackList).where(BlackList.id == id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_blacklists(self) -> AsyncIterator[BlackList]:
        async with self._async_session() as session:
            async for blacklist in BlackList.read_all(session):
                yield blacklist

    async def delete_blacklist(self, id: int, /) -> None:
        async with self._async_session() as session:
            blacklist = await BlackList.read_by_id(session, id)
            if not blacklist:
                raise BlacklistDoesNotExist(f"blacklist with id {id!r} does not exist")
            await BlackList.delete(session, blacklist)
            await session.commit()
            self._log.info(f'deleted blacklist with id {id!r}')

    # command

    async def create_app_command(
        self,
        guild: Optional[int],
        channel: int,
        author: int,
        used: datetime.datetime,
        command: str,
        failed: bool,
    ) -> AppCommand:
        async with self._async_session() as session:
            cmd = await AppCommand.create(
                session=session,
                guild=guild,
                channel=channel,
                author=author,
                used=used,
                command=command,
                failed=failed,
            )
            await session.commit()
            self._log.info(f'created app command with id {command!r}')
            return cmd

    async def get_app_commands(self) -> AsyncIterator[AppCommand]:
        async with self._async_session() as session:
            async for cmd in AppCommand.read_all(session):
                yield cmd

    async def get_app_commands_by_name(self, name: str) -> AsyncIterator[AppCommand]:
        async with self._async_session() as session:
            async for cmd in AppCommand.read_all_by_name(session, name):
                yield cmd

    # riot account

    async def create_riot_account(
        self,
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
        owner_id: int,
    ) -> RiotAccount:
        async with self._async_session() as session:
            exist_account = await RiotAccount.read_by_puuid_and_owner_id(session, puuid, owner_id)
            if exist_account:
                raise RiotAccountAlreadyExists(f"riot account with id {puuid!r} already exists")
            riot_account = await RiotAccount.create(
                session=session,
                puuid=puuid,
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
                owner_id=owner_id,
            )
            await session.commit()

            self._log.info(f'created riot account {game_name}#{tag_line}({puuid}) for user with id {owner_id}')
            return riot_account

    async def get_riot_account_by_puuid_and_owner_id(self, puuid: str, owner_id: int) -> Optional[RiotAccount]:
        async with self._async_session() as session:
            riot_account = await RiotAccount.read_by_puuid_and_owner_id(session, puuid, owner_id)
            return riot_account

    async def get_riot_accounts_by_puuid_and_owner_id(self, id: int, /) -> AsyncIterator[RiotAccount]:
        async with self._async_session() as session:
            async for riot_account in RiotAccount.read_all_by_owner_id(session, id):
                yield riot_account

    async def get_riot_accounts(self) -> AsyncIterator[RiotAccount]:
        async with self._async_session() as session:
            async for riot_account in RiotAccount.read_all(session):
                yield riot_account

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
    ) -> bool:
        async with self._async_session() as session:
            riot_account = await RiotAccount.read_by_puuid_and_owner_id(session, puuid, owner_id)
            if not riot_account:
                raise RiotAccountDoesNotExist(f"riot account with puuid {puuid!r} does not exist")
            try:
                await riot_account.update(
                    session=session,
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
                )
            except SQLAlchemyError as e:
                self._log.error(f'failed to update riot account with puuid {puuid!r} for user id {owner_id!r}: {e!r}')
                await session.rollback()
                return False
            else:
                await session.commit()
                self._log.info(f'updated riot account with puuid {puuid!r} for user with id {owner_id!r}')
                return True

    async def delete_riot_account(self, puuid: str, owner_id: int) -> bool:
        async with self._async_session() as session:
            riot_account = await RiotAccount.read_by_puuid_and_owner_id(session, puuid, owner_id)
            if not riot_account:
                raise RiotAccountDoesNotExist(f"riot account with puuid {puuid!r} does not exist")

            try:
                await RiotAccount.delete(session, riot_account)
            except SQLAlchemyError as e:
                self._log.error(
                    f'failed to delete riot account with puuid {puuid!r} for user with id {owner_id!r}: {e!r}'
                )
                await session.rollback()
                return False
            else:
                await session.commit()
                self._log.info(f'deleted riot account with puuid {puuid!r} for user with id {owner_id!r}')
                return True

    async def delete_all_riot_accounts(self, owner_id: int) -> bool:
        async with self._async_session() as session:
            try:
                await RiotAccount.delete_all_by_owner_id(session, owner_id)
            except SQLAlchemyError as e:
                self._log.error(f'failed to delete all riot accounts for user with id {owner_id!r}: {e!r}')
                await session.rollback()
                return False
            else:
                await session.commit()
                self._log.info(f'deleted all riot accounts for user with id {owner_id!r}')
                return True
