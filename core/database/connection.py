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
    NotificationAlreadyExists,
    NotificationDoesNotExist,
    NotificationSettingsAlreadyExists,
    NotificationSettingsDoesNotExist,
    RiotAccountAlreadyExists,
    RiotAccountDoesNotExist,
    UserAlreadyExists,
    UserDoesNotExist,
)
from .models.app_command import AppCommand
from .models.base import Base
from .models.blacklist import BlackList
from .models.notification import Notification
from .models.notification_settings import NotificationSettings
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
        self._log.info('creating tables')
        async with self._async_engine.begin() as engine:
            if drop:
                await engine.run_sync(Base.metadata.drop_all)
            await engine.run_sync(Base.metadata.create_all)
        self._log.info('tables created')

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
                raise UserAlreadyExists(id)
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

    async def update_user(
        self,
        id: int,
        *,
        locale: Optional[str] = None,
        main_account_id: Optional[int] = None,
    ) -> bool:
        async with self._async_session() as session:
            user = await User.read_by_id(session, id)
            if not user:
                raise UserDoesNotExist(id)
            try:
                await user.update(session, locale, main_account_id)
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
                raise UserDoesNotExist(id)
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
                raise BlacklistAlreadyExists(id)
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
                raise BlacklistDoesNotExist(id)
            await BlackList.delete(session, blacklist)
            await session.commit()
            self._log.info(f'deleted blacklist with id {id!r}')

    # command

    async def create_app_command(
        self,
        type: int,
        guild: Optional[int],
        channel: Optional[int],
        author: int,
        used: datetime.datetime,
        command: str,
        failed: bool,
    ) -> AppCommand:
        async with self._async_session() as session:
            cmd = await AppCommand.create(
                type=type,
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
        owner_id: int,
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
        incognito: bool = False,
        notify: bool = False,
    ) -> RiotAccount:
        async with self._async_session() as session:
            exist_account = await RiotAccount.read_by_puuid_and_owner_id(session, puuid, owner_id)
            if exist_account:
                raise RiotAccountAlreadyExists(puuid, owner_id)
            riot_account = await RiotAccount.create(
                session=session,
                owner_id=owner_id,
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
                incognito=incognito,
                notify=notify,
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
        incognito: Optional[bool] = None,
        notify: Optional[bool] = None,
    ) -> bool:
        async with self._async_session() as session:
            riot_account = await RiotAccount.read_by_puuid_and_owner_id(session, puuid, owner_id)
            if not riot_account:
                raise RiotAccountDoesNotExist(puuid, owner_id)
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
                    incognito=incognito,
                    notify=notify,
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
                raise RiotAccountDoesNotExist(puuid, owner_id)

            try:
                await RiotAccount.delete(session, riot_account)
            except SQLAlchemyError as e:
                self._log.error(f'failed to delete riot account with puuid {puuid!r} for user with id {owner_id!r}: {e!r}')
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

    # notification

    async def create_notification(
        self,
        owner_id: int,
        *,
        item_id: str,
        type: str,
    ) -> Notification:
        async with self._async_session() as session:
            existing_notification = await Notification.read_by_owner_id_and_item_id(session, owner_id, item_id)
            if existing_notification:
                raise NotificationAlreadyExists(owner_id, item_id)
            notification = await Notification.create(
                session=session,
                owner_id=owner_id,
                item_id=item_id,
                type=type,
            )
            await session.commit()
            self._log.info(f'created notification for user with id {owner_id}')
            return notification

    async def get_notifications_by_owner_id(self, owner_id: int, /) -> AsyncIterator[Notification]:
        async with self._async_session() as session:
            async for notification in Notification.read_all_by_owner_id(session, owner_id):
                yield notification

    async def get_notification_by_owner_id_and_item_id(self, owner_id: int, /, *, item_id: str) -> Optional[Notification]:
        async with self._async_session() as session:
            notification = await Notification.read_by_owner_id_and_item_id(session, owner_id, item_id)
            return notification

    async def get_notifications_by_owner_id_and_type(self, owner_id: int, /, *, type: str) -> AsyncIterator[Notification]:
        async with self._async_session() as session:
            async for notification in Notification.read_all_by_owner_id_and_type(session, owner_id, type):
                yield notification

    async def delete_notification(self, owner_id: int, /, *, item_id: str, type: str) -> bool:
        async with self._async_session() as session:
            notification = await Notification.read_by_owner_id_and_item_id(session, owner_id, item_id)
            if not notification:
                raise NotificationDoesNotExist(owner_id, item_id)

            try:
                await Notification.delete(session, notification)
            except SQLAlchemyError as e:
                self._log.error(f'failed to delete notification for user with id {owner_id!r}: {e!r}')
                await session.rollback()
                return False
            else:
                await session.commit()
                self._log.info(f'deleted notification for user with id {owner_id!r}')
                return True

    async def delete_notification_by_owner_id_and_item_id(self, owner_id: int, /, *, item_id: str) -> bool:
        async with self._async_session() as session:
            notification = await Notification.read_by_owner_id_and_item_id(session, owner_id, item_id)
            if not notification:
                raise NotificationDoesNotExist(owner_id, item_id)

            try:
                await Notification.delete(session, notification)
            except SQLAlchemyError as e:
                self._log.error(f'failed to delete notification for user with id {owner_id!r}: {e!r}')
                await session.rollback()
                return False
            else:
                await session.commit()
                self._log.info(f'deleted notification for user with id {owner_id!r}')
                return True

    async def delete_all_notifications(self, owner_id: int, /) -> bool:
        async with self._async_session() as session:
            try:
                await Notification.delete_all_by_owner_id(session, owner_id)
            except SQLAlchemyError as e:
                self._log.error(f'failed to delete all notifications for user with id {owner_id!r}: {e!r}')
                await session.rollback()
                return False
            else:
                await session.commit()
                self._log.info(f'deleted all notifications for user with id {owner_id!r}')
                return True

    # notification settings

    async def create_notification_settings(
        self,
        owner_id: int,
        *,
        channel_id: int,
        mode: int,
        enabled: bool,
    ) -> NotificationSettings:
        async with self._async_session() as session:
            existing_settings = await NotificationSettings.read_by_owner_id(session, owner_id)
            if existing_settings:
                raise NotificationSettingsAlreadyExists(owner_id)
            settings = await NotificationSettings.create(
                session=session,
                owner_id=owner_id,
                channel_id=channel_id,
                mode=mode,
                enabled=enabled,
            )
            await session.commit()
            self._log.info(f'created notification settings for user with id {owner_id}')
            return settings

    async def get_notification_settings_by_owner_id(self, owner_id: int, /) -> Optional[NotificationSettings]:
        async with self._async_session() as session:
            settings = await NotificationSettings.read_by_owner_id(session, owner_id)
            return settings

    async def update_notification_settings(
        self,
        owner_id: int,
        *,
        channel_id: Optional[int] = None,
        mode: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[NotificationSettings]:
        async with self._async_session() as session:
            settings = await NotificationSettings.read_by_owner_id(session, owner_id)
            if not settings:
                raise NotificationSettingsDoesNotExist(owner_id)

            try:
                await settings.update(session, channel_id=channel_id, mode=mode, enabled=enabled)
            except SQLAlchemyError as e:
                self._log.error(f'failed to update notification settings for user with id {owner_id!r}: {e!r}')
                await session.rollback()
                return None
            else:
                await session.commit()
                self._log.info(f'updated notification settings for user with id {owner_id!r}')
                return settings

    async def delete_notification_settings(self, owner_id: int, /) -> bool:
        async with self._async_session() as session:
            settings = await NotificationSettings.read_by_owner_id(session, owner_id)
            if not settings:
                raise NotificationSettingsDoesNotExist(owner_id)

            try:
                await NotificationSettings.delete(session, settings)
            except SQLAlchemyError as e:
                self._log.error(f'failed to delete notification settings for user with id {owner_id!r}: {e!r}')
                await session.rollback()
                return False
            else:
                await session.commit()
                self._log.info(f'deleted notification settings for user with id {owner_id!r}')
                return True
