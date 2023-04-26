from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Optional

from sqlalchemy import ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class RiotAuth(Base):
    __tablename__ = "riot_auths"

    id: Mapped[str] = mapped_column("id", nullable=False, unique=True, primary_key=True)
    name: Mapped[str] = mapped_column("name", nullable=False)
    tag: Mapped[str] = mapped_column("tag", nullable=False)
    secrets: Mapped[str] = mapped_column("secrets", nullable=False)
    owner_id: Mapped[int] = mapped_column("owner_id", ForeignKey("users.id"), nullable=False)
    owner: Mapped[User] = relationship("User", back_populates="riot_auths", lazy="joined", uselist=False)

    @property
    def puuid(self) -> str:
        return self.id

    @hybrid_property
    def locale(self) -> str:
        return self.owner.locale

    @classmethod
    async def read_all(cls, session: AsyncSession) -> AsyncIterator[RiotAuth]:
        stmt = select(cls).options(joinedload(cls.owner, innerjoin=True))
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def read_by_id(cls, session: AsyncSession, puuid: str) -> Optional[RiotAuth]:
        stmt = select(cls).where(cls.id == id).options(joinedload(cls.owner))
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def read_by_ids(cls, session: AsyncSession, puuids: list[str]) -> AsyncIterator[RiotAuth]:
        stmt = select(cls).where(cls.id.in_(puuids)).options(joinedload(cls.owner))  # type: ignore
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def create(
        cls, session: AsyncSession, user_id: int, puuid: str, name: str, tag: str, secrets: str
    ) -> RiotAuth:
        riot_auth = RiotAuth(id=puuid, name=name, tag=tag, secrets=secrets, user_id=user_id)
        session.add(riot_auth)
        await session.flush()

        # To fetch the riot auth
        new = await cls.read_by_id(session, riot_auth.id)
        if not new:
            raise RuntimeError()
        return new

    # async def update(
    #     self, session: AsyncSession, notebook_id: int, title: str, content: str
    # ) -> None:
    #     self.notebook_id = notebook_id
    #     self.title = title
    #     self.content = content
    #     await session.flush()

    @classmethod
    async def delete(cls, session: AsyncSession, riot_auth: RiotAuth) -> None:
        await session.delete(riot_auth)
        await session.flush()
