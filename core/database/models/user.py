from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Optional

from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

if TYPE_CHECKING:
    from typing_extensions import Self

# fmt: off
__all__ = (
    'User',
)
# fmt: off

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column('id', nullable=False, unique=True, primary_key=True)  # autoincrement=True,
    locale: Mapped[str] = mapped_column('locale', String(length=10), nullable=False, default='en_US')

    async def update(self, session: AsyncSession, locale: str) -> None:
        self.locale = locale
        await session.flush()

    @classmethod
    async def read_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls)
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def read_by_id(cls, session: AsyncSession, id: int) -> Optional[Self]:
        stmt = select(cls).where(cls.id == id)
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def create(cls, session: AsyncSession, id: int, locale: str) -> Self:
        user = User(id=id, locale=locale)
        session.add(user)
        await session.flush()
        # To fetch accounts
        new = await cls.read_by_id(session, user.id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, user: Self) -> None:
        await session.delete(user)
        await session.flush()
