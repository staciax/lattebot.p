from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, AsyncIterator

from sqlalchemy import ForeignKey, String, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from typing_extensions import Self

    from .user import User

# fmt: off
__all__ = (
    'Notification',
)
# fmt: on


class Notification(Base):
    __tablename__ = 'notifications'

    id: Mapped[int] = mapped_column('id', primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column('item_id', String(36), nullable=False)
    owner_id: Mapped[int] = mapped_column('owner_id', ForeignKey('users.id'), nullable=False)
    owner: Mapped[User] = relationship('User', lazy='joined')
    type: Mapped[str] = mapped_column('type', String(36), nullable=False)
    registered_at: Mapped[datetime.datetime] = mapped_column('created_at', nullable=False, default=datetime.datetime.utcnow)

    @classmethod
    async def find_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls)
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def find_by_id(cls, session: AsyncSession, id: int) -> Self | None:
        stmt = select(cls).where(cls.id == id)
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def find_all_by_owner_id(cls, session: AsyncSession, owner_id: int) -> AsyncIterator[Self]:
        stmt = select(cls).where(cls.owner_id == owner_id)
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def find_by_owner_id_and_item_id(cls, session: AsyncSession, owner_id: int, item_id: str) -> Self | None:
        stmt = select(cls).where(cls.owner_id == owner_id).where(cls.item_id == item_id)
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def find_all_by_owner_id_and_type(cls, session: AsyncSession, owner_id: int, type: str) -> AsyncIterator[Self]:
        stmt = select(cls).where(cls.owner_id == owner_id).where(cls.type == type)
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def create(cls, session: AsyncSession, owner_id: int, item_id: str, type: str) -> Self:
        notify = Notification(
            owner_id=owner_id,
            item_id=item_id,
            type=type,
        )
        session.add(notify)
        await session.flush()
        new = await cls.find_by_id(session, notify.id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, notification: Self) -> None:
        await session.delete(notification)
        await session.flush()

    @classmethod
    async def delete_all_by_owner_id(cls, session: AsyncSession, owner_id: int) -> None:
        stmt = delete(cls).where(cls.owner_id == owner_id)
        await session.execute(stmt)
        await session.flush()
