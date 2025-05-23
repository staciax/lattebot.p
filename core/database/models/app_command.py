from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, AsyncIterator

from sqlalchemy import ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from typing_extensions import Self

    from .user import User

# fmt: off
__all__ = (
    'AppCommand',
)
# fmt: on


class AppCommand(Base):
    __tablename__ = 'app_commands'

    id: Mapped[int] = mapped_column('id', primary_key=True, autoincrement=True)
    type: Mapped[int] = mapped_column('type', default=1)
    guild: Mapped[int | None] = mapped_column('guild_id')
    channel: Mapped[int | None] = mapped_column('channel')
    author_id: Mapped[int] = mapped_column('author_id', ForeignKey('users.id'))
    used: Mapped[datetime.datetime] = mapped_column('used', default=datetime.datetime.utcnow)
    command: Mapped[str] = mapped_column('command', String(length=256))
    failed: Mapped[bool] = mapped_column('failed', default=False)
    author: Mapped[User] = relationship('User', back_populates='app_command_uses')

    @classmethod
    async def find_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls)
        stream = await session.stream_scalars(stmt.order_by(cls.used))
        async for row in stream:
            yield row

    @classmethod
    async def find_by_id(cls, session: AsyncSession, id: int) -> Self | None:
        stmt = select(cls).where(cls.id == id)
        return await session.scalar(stmt.order_by(cls.used))

    @classmethod
    async def find_by_guild_id(cls, session: AsyncSession, guild_id: int) -> Self | None:
        stmt = select(cls).where(cls.guild == guild_id)
        return await session.scalar(stmt.order_by(cls.used))

    @classmethod
    async def find_by_name(cls, session: AsyncSession, name: str) -> Self | None:
        stmt = select(cls).where(cls.command == name)
        return await session.scalar(stmt.order_by(cls.used))

    @classmethod
    async def find_all_by_name(cls, session: AsyncSession, name: str) -> AsyncIterator[Self]:
        stmt = select(cls).where(cls.command == name)
        stream = await session.stream_scalars(stmt.order_by(cls.used))
        async for row in stream:
            yield row

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        type: int,
        guild: int | None,
        channel: int | None,
        author: int,
        used: datetime.datetime,
        command: str,
        failed: bool,
    ) -> Self:
        cmd = AppCommand(
            type=type,
            guild=guild,
            channel=channel,
            author_id=author,
            used=used,
            command=command,
            failed=failed,
        )
        session.add(cmd)
        await session.flush()
        # To fetch the new object from the database, we need to refresh it.
        new = await cls.find_by_id(session, cmd.id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete_all_by_author_id(cls, session: AsyncSession, author_id: int) -> None:
        stmt = select(cls).where(cls.author_id == author_id)
        await session.delete(stmt)
        await session.flush()
