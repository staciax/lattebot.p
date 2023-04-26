from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, List, Optional

from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from .base import Base

if TYPE_CHECKING:
    from .riot_auth import RiotAuth


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column("id", nullable=False, unique=True, primary_key=True)  # autoincrement=True,
    locale: Mapped[str] = mapped_column("locale", String(length=10), nullable=False)
    riot_auths: Mapped[List[RiotAuth]] = relationship(
        "RiotAuth",
        back_populates="user",
        order_by="RiotAuth.id",
        cascade="save-update, merge, refresh-expire, expunge, delete, delete-orphan",
    )

    @classmethod
    async def read_all(cls, session: AsyncSession, include_riot_auths: bool) -> AsyncIterator[User]:
        stmt = select(cls)
        if include_riot_auths:
            stmt = stmt.options(selectinload(cls.riot_auths))
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def read_by_id(cls, session: AsyncSession, user_id: int, include_riot_auths: bool = False) -> Optional[User]:
        stmt = select(cls).where(cls.id == user_id)
        if include_riot_auths:
            stmt = stmt.options(selectinload(cls.riot_auths))
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def create(cls, session: AsyncSession, user_id: int, locale: str, riot_auths: List[RiotAuth]) -> User:
        user = User(
            id=user_id,
            locale=locale,
            riot_auths=riot_auths,
        )
        session.add(user)
        await session.flush()
        # To fetch riot_auths
        new = await cls.read_by_id(session, user.id, include_riot_auths=True)
        if not new:
            raise RuntimeError()
        return new

    async def update(self, session: AsyncSession, locale: str, riot_auths: List[RiotAuth]) -> None:
        self.locale = locale
        self.riot_auths = riot_auths
        await session.flush()

    @classmethod
    async def delete(cls, session: AsyncSession, user: User) -> None:
        await session.delete(user)
        await session.flush()
