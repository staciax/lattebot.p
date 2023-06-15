from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Optional

from sqlalchemy import ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from typing_extensions import Self

    from .user import User

# fmt: off
__all__ = (
    'BlackList',
)
# fmt: off

class BlackList(Base):
    __tablename__ = 'blacklist'

    id: Mapped[int] = mapped_column('id', ForeignKey('users.id'), nullable=False, unique=True, primary_key=True)
    reason: Mapped[Optional[str]] = mapped_column('reason', String(length=2000), nullable=True, default=None)
    maybe_user: Mapped[Optional[User]] = relationship(
        'User',
        back_populates='blacklist', 
        lazy='joined',
    )

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} id={self.id} reason={self.reason!r}>'

    @property
    def object_id(self) -> int:
        return self.id

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
    async def create(cls, session: AsyncSession, id: int, reason: Optional[str] = None) -> Self:
        blacklist = BlackList(
            id=id,
            reason=reason,
        )
        session.add(blacklist)
        await session.flush()
        new = await cls.read_by_id(session, blacklist.id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, blacklist: Self) -> None:
        await session.delete(blacklist)
        await session.flush()
