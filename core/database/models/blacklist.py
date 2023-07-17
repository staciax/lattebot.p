from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, AsyncIterator

from sqlalchemy import ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from typing_extensions import Self

    from .user import User

# fmt: off
__all__ = (
    'BlackList',
)
# fmt: on


class BlackList(Base):
    __tablename__ = 'blacklist'

    object_id: Mapped[int] = mapped_column('object_id', ForeignKey('users.id'), primary_key=True, autoincrement=False)
    object: Mapped[User | None] = relationship('User', lazy='joined', viewonly=True, back_populates='blacklist')
    reason: Mapped[str | None] = mapped_column('reason', String(length=2000), nullable=True, default=None)
    banned_at: Mapped[datetime.datetime] = mapped_column('banned_at', default=datetime.datetime.utcnow)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} object_id={self.object_id} reason={self.reason!r}>'

    @hybrid_property
    def id(self) -> int:
        return self.object_id

    @hybrid_method
    def is_user(self) -> bool:
        return self.object is not None

    @classmethod
    async def find_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls)
        stream = await session.stream_scalars(stmt.order_by(cls.object_id))
        async for row in stream.unique():
            yield row

    @classmethod
    async def find_by_id(cls, session: AsyncSession, object_id: int) -> Self | None:
        stmt = select(cls).where(cls.object_id == object_id)
        return await session.scalar(stmt.order_by(cls.object_id))

    @classmethod
    async def create(cls, session: AsyncSession, object_id: int, reason: str | None = None) -> Self:
        blacklist = BlackList(
            object_id=object_id,
            reason=reason,
        )
        session.add(blacklist)
        await session.flush()
        new = await cls.find_by_id(session, blacklist.object_id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, blacklist: Self) -> None:
        await session.delete(blacklist)
        await session.flush()
