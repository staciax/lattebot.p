from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Self  # noqa: UP035

from sqlalchemy import ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship  # foreign, _

from .base import Base

if TYPE_CHECKING:

    from .riot_account import RiotAccount
    from .user import User

# fmt: off
__all__ = (
    'RiotAccountSettings',
)
# fmt: on


class RiotAccountSettings(Base):
    __tablename__ = 'riot_account_settings'

    user_id: Mapped[int] = mapped_column('user_id', ForeignKey('users.id'), primary_key=True, autoincrement=False)
    user: Mapped[User] = relationship('User', lazy='joined')
    current_account: Mapped[RiotAccount | None] = relationship('RiotAccount', lazy='joined', viewonly=True)
    current_account_id: Mapped[int | None] = mapped_column(
        'current_account_id',
        ForeignKey('riot_accounts.id'),
        default=None,
    )

    @classmethod
    async def find_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls)
        stream = await session.stream_scalars(stmt)
        async for row in stream:
            yield row

    @classmethod
    async def find_by_user_id(cls, session: AsyncSession, user_id: int) -> Self | None:
        stmt = select(cls).where(cls.user_id == user_id)
        return await session.scalar(stmt)

    @classmethod
    async def create(cls, session: AsyncSession, user_id: int) -> Self:
        settings = RiotAccountSettings(user_id=user_id)
        session.add(settings)
        await session.flush()
        # To fetch the new object
        new = await cls.find_by_user_id(session, user_id)
        if not new:
            raise RuntimeError()
        return new

    async def update(self, session: AsyncSession, **kwargs) -> Self:
        self.current_account_id = kwargs.get('current_account_id', self.current_account_id)
        await session.flush()
        # To fetch the new object
        new = await self.find_by_user_id(session, self.user_id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, riot_account_settings: Self) -> None:
        await session.delete(riot_account_settings)
        await session.flush()
