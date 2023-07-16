from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, AsyncIterator

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from typing_extensions import Self

    from .app_command import AppCommand
    from .blacklist import BlackList
    from .notification_settings import NotificationSettings
    from .riot_account import RiotAccount
    from .riot_account_settings import RiotAccountSettings
    from .user_settings import UserSettings

# fmt: off
__all__ = (
    'User',
)
# fmt: on


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column('id', nullable=False, unique=True, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column('user_id', nullable=False, unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column('created_at', nullable=False, default=datetime.datetime.utcnow)
    user_settings: Mapped[UserSettings | None] = relationship(
        'UserSettings',
        back_populates='user',
        lazy='joined',
        cascade='save-update, merge, refresh-expire, expunge, delete, delete-orphan',
    )
    notification_settings: Mapped[NotificationSettings | None] = relationship(
        'NotificationSettings',
        back_populates='owner',
        lazy='joined',
        viewonly=True,
    )
    blacklist: Mapped[BlackList | None] = relationship(
        'BlackList',
        back_populates='object',
        lazy='joined',
        viewonly=True,
    )
    app_command_uses: Mapped[list[AppCommand]] = relationship(
        'AppCommand',
        back_populates='author',
        order_by='AppCommand.used',
        lazy='selectin',
        viewonly=True,
    )
    riot_accounts: Mapped[list[RiotAccount]] = relationship(
        'RiotAccount',
        back_populates='owner',
        cascade='save-update, merge, refresh-expire, expunge, delete, delete-orphan',
        lazy='selectin',
    )
    riot_account_settings: Mapped[RiotAccountSettings | None] = relationship(
        'RiotAccountSettings',
        back_populates='user',
        lazy='joined',
        cascade='save-update, merge, refresh-expire, expunge, delete, delete-orphan',
    )

    @hybrid_property
    def locale(self) -> str | None:
        if self.user_settings is None:
            return None
        return self.user_settings.locale

    @hybrid_method
    def is_blacklisted(self) -> bool:
        return self.blacklist is not None

    @hybrid_method
    def get_riot_account(self, puuid: str, /) -> RiotAccount | None:
        for account in self.riot_accounts:
            if account.puuid == puuid:
                return account
        return None

    async def update(
        self,
        session: AsyncSession,
        locale: str | None = None,
        main_riot_account_id: int | None = None,
    ) -> Self:
        if locale is not None:
            self.locale = locale
        if main_riot_account_id is not None:
            self.main_riot_account_id = main_riot_account_id
        await session.flush()
        # To fetch the new object
        new = await self.read_by_id(session, self.id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def read_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls).options()
        stream = await session.stream_scalars(stmt.order_by(cls.id).distinct())
        async for row in stream.unique():
            yield row

    @classmethod
    async def read_by_id(cls, session: AsyncSession, user_id: int) -> Self | None:
        stmt = select(cls).where(cls.user_id == user_id)
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def create(cls, session: AsyncSession, user_id: int) -> Self:
        user = User(user_id=user_id)
        session.add(user)
        await session.flush()
        # To fetch accounts
        new = await cls.read_by_id(session, user.id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, user: Self) -> None:
        stmt = delete(cls).where(cls.id == user.id)
        # await session.delete(user)
        await session.execute(stmt)
        await session.flush()
