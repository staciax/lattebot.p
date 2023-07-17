# import sqlalchemy
import asyncio
import datetime
import logging
from typing import AsyncIterator

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
from .models.riot_account_settings import RiotAccountSettings
from .models.user import User
from .models.user_settings import UserSettings

# fmt: off
__all__ = (
    'DatabaseConnection',
)
# fmt: on

# TODO: improvement python typing to 3.9+


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

    async def fetch_session(self) -> AsyncSession:
        return self._async_session()

    # user

    async def add_user(self, id: int, /) -> User:
        async with self._async_session() as session:
            exist_user = await User.read_by_id(session, id)
            if exist_user:
                raise UserAlreadyExists(id)
            user = await User.create(session=session, id=id)
            await session.commit()
            self._log.info(f'created user with id {id!r}')
            return user

    async def fetch_user(self, id: int, /) -> User | None:
        async with self._async_session() as session:
            user = await User.read_by_id(session, id)
            return user

    async def fetch_users(self) -> AsyncIterator[User]:
        async with self._async_session() as session:
            async for user in User.read_all(session):
                yield user

    async def update_user(self, id: int, /) -> User | None:
        async with self._async_session() as session:
            user = await User.read_by_id(session, id)
            if not user:
                raise UserDoesNotExist(id)
            try:
                new = await user.update(session)
            except SQLAlchemyError as e:
                await session.rollback()
                self._log.error(f'failed to update user with id {id!r} due to {e!r}')
                return None
            else:
                await session.commit()
                log_msg = f'updated user with id {id!r}'
                self._log.info(log_msg)
                return new

    async def remove_user(self, id: int, /) -> bool:
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

    async def add_blacklist(self, object_id: int, *, reason: str | None = None) -> BlackList:
        async with self._async_session() as session:
            exist_blacklist = await BlackList.read_by_id(session, object_id)
            if exist_blacklist:
                raise BlacklistAlreadyExists(object_id)
            blacklist = await BlackList.create(session=session, object_id=object_id, reason=reason)
            await session.commit()
            self._log.info(f'created blacklist with id {id!r}')
            return blacklist

    async def fetch_blacklist(self, id: int, /) -> BlackList | None:
        async with self._async_session() as session:
            stmt = select(BlackList).where(BlackList.id == id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def fetch_blacklists(self) -> AsyncIterator[BlackList]:
        async with self._async_session() as session:
            async for blacklist in BlackList.read_all(session):
                yield blacklist

    async def remove_blacklist(self, id: int, /) -> None:
        async with self._async_session() as session:
            blacklist = await BlackList.read_by_id(session, id)
            if not blacklist:
                raise BlacklistDoesNotExist(id)
            await BlackList.delete(session, blacklist)
            await session.commit()
            self._log.info(f'deleted blacklist with id {id!r}')

    # command

    async def add_app_command(
        self,
        type: int,
        guild: int | None,
        channel: int | None,
        author: int,
        used: datetime.datetime,
        command: str,
        failed: bool,
    ) -> AppCommand:
        async with self._async_session() as session:
            app_command = await AppCommand.create(
                session=session,
                type=type,
                guild=guild,
                channel=channel,
                author=author,
                used=used,
                command=command,
                failed=failed,
            )
            await session.commit()
            self._log.info(f'created app command {app_command.command!r}')
            return app_command

    async def fetch_app_commands(self) -> AsyncIterator[AppCommand]:
        async with self._async_session() as session:
            async for app_command in AppCommand.read_all(session):
                yield app_command

    async def fetch_app_commands_by_name(self, name: str) -> AsyncIterator[AppCommand]:
        async with self._async_session() as session:
            async for app_command in AppCommand.read_all_by_name(session, name):
                yield app_command

    # riot account

    async def add_riot_account(
        self,
        owner_id: int,
        *,
        puuid: str,
        game_name: str | None,
        tag_line: str | None,
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

    async def fetch_riot_account_by_puuid_and_owner_id(self, puuid: str, owner_id: int) -> RiotAccount | None:
        async with self._async_session() as session:
            riot_account = await RiotAccount.read_by_puuid_and_owner_id(session, puuid, owner_id)
            return riot_account

    async def fetch_riot_accounts_by_puuid_and_owner_id(self, id: int, /) -> AsyncIterator[RiotAccount]:
        async with self._async_session() as session:
            async for riot_account in RiotAccount.read_all_by_owner_id(session, id):
                yield riot_account

    async def fetch_riot_accounts(self) -> AsyncIterator[RiotAccount]:
        async with self._async_session() as session:
            async for riot_account in RiotAccount.read_all(session):
                yield riot_account

    async def update_riot_account(
        self,
        puuid: str,
        owner_id: int,
        *,
        game_name: str | None = None,
        tag_line: str | None = None,
        region: str | None = None,
        scope: str | None = None,
        token_type: str | None = None,
        expires_at: int | None = None,
        id_token: str | None = None,
        access_token: str | None = None,
        entitlements_token: str | None = None,
        ssid: str | None = None,
        incognito: bool | None = None,
        notify: bool | None = None,
        display_name: str | None = None,
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
                    display_name=display_name,
                )
            except SQLAlchemyError as e:
                self._log.error(f'failed to update riot account with puuid {puuid!r} for user id {owner_id!r}: {e!r}')
                await session.rollback()
                return False
            else:
                await session.commit()
                self._log.info(f'updated riot account with puuid {puuid!r} for user with id {owner_id!r}')
                return True

    async def remove_riot_account(self, puuid: str, owner_id: int) -> RiotAccount | None:
        async with self._async_session() as session:
            riot_account = await RiotAccount.read_by_puuid_and_owner_id(session, puuid, owner_id)
            if not riot_account:
                raise RiotAccountDoesNotExist(puuid, owner_id)

            try:
                await RiotAccount.delete(session, riot_account)
            except SQLAlchemyError as e:
                self._log.error(f'failed to delete riot account with puuid {puuid!r} for user with id {owner_id!r}: {e!r}')
                await session.rollback()
                return None
            else:
                await session.commit()
                self._log.info(f'deleted riot account with puuid {puuid!r} for user with id {owner_id!r}')
                return riot_account

    async def remove_riot_accounts(self, owner_id: int) -> bool:
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

    async def add_notification(
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

    async def fetch_notifications_by_owner_id(self, owner_id: int, /) -> AsyncIterator[Notification]:
        async with self._async_session() as session:
            async for notification in Notification.read_all_by_owner_id(session, owner_id):
                yield notification

    async def fetch_notification_by_owner_id_and_item_id(self, owner_id: int, /, *, item_id: str) -> Notification | None:
        async with self._async_session() as session:
            notification = await Notification.read_by_owner_id_and_item_id(session, owner_id, item_id)
            return notification

    async def fetch_notifications_by_owner_id_and_type(self, owner_id: int, /, *, type: str) -> AsyncIterator[Notification]:
        async with self._async_session() as session:
            async for notification in Notification.read_all_by_owner_id_and_type(session, owner_id, type):
                yield notification

    async def remove_notification(self, owner_id: int, /, *, item_id: str, type: str) -> bool:
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

    async def remove_notification_by_owner_id_and_item_id(self, owner_id: int, /, *, item_id: str) -> bool:
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

    async def remove_notifications(self, owner_id: int, /) -> bool:
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

    async def add_notification_settings(
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

    async def fetch_notification_settings_by_owner_id(self, owner_id: int, /) -> NotificationSettings | None:
        async with self._async_session() as session:
            settings = await NotificationSettings.read_by_owner_id(session, owner_id)
            return settings

    async def update_notification_settings(
        self,
        owner_id: int,
        *,
        channel_id: int | None = None,
        mode: int | None = None,
        enabled: bool | None = None,
    ) -> NotificationSettings | None:
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

    async def remove_notification_settings(self, owner_id: int, /) -> bool:
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
