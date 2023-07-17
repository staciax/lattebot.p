from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from sqlalchemy import ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship  # foreign

from .base import Base

if TYPE_CHECKING:
    from typing_extensions import Self

    from .user import User

# fmt: off
__all__ = (
    'UserSettings',
)
# fmt: on


class UserSettings(Base):
    __tablename__ = 'user_settings'

    user_id: Mapped[int] = mapped_column('user_id', ForeignKey('users.id'), primary_key=True, autoincrement=False)
    user: Mapped[User] = relationship('User', lazy='joined', back_populates='settings')
    locale: Mapped[str | None] = mapped_column('locale', String(length=10), nullable=False)
    notification: Mapped[bool] = mapped_column('notification', default=False)

    @classmethod
    async def find_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls).join(User)
        stream = await session.stream_scalars(stmt)
        async for row in stream:
            yield row

    @classmethod
    async def find_by_user_id(cls, session: AsyncSession, user_id: int) -> Self | None:
        stmt = select(cls).where(cls.user_id == user_id)
        return await session.scalar(stmt)

    @classmethod
    async def create(cls, session: AsyncSession, user_id: int, locale: str, notification: bool) -> Self:
        settings = UserSettings(user_id=user_id, locale=locale, notification=notification)
        session.add(settings)
        await session.flush()
        # To fetch the new object
        new = await cls.find_by_user_id(session, user_id)
        if not new:
            raise RuntimeError()
        return new

    async def update(self, session: AsyncSession, **kwargs) -> Self:
        self.locale = kwargs.get('locale', self.locale)
        self.notification = kwargs.get('notification', self.notification)
        await session.flush()
        # To fetch the new object
        new = await self.find_by_user_id(session, self.user_id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, settings: Self) -> None:
        await session.delete(settings)
        await session.flush()
