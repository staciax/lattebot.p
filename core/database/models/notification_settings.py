from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Self  # noqa: UP035

from sqlalchemy import ForeignKey, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import Mapped, mapped_column, relationship  # foreign

from .base import Base

if TYPE_CHECKING:
    from .notification import Notification
    from .user import User

# fmt: off
__all__ = (
    'NotificationSettings',
)
# fmt: on


class NotificationSettings(Base):
    __tablename__ = 'notification_settings'

    owner_id: Mapped[int] = mapped_column('owner_id', ForeignKey('users.id'), primary_key=True, autoincrement=False)
    owner: Mapped[User] = relationship('User', lazy='joined')
    channel_id: Mapped[int] = mapped_column('channel_id', nullable=False, default=0)
    mode: Mapped[int] = mapped_column('mode', nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column('enabled', nullable=False, default=False)
    notifications: Mapped[list[Notification]] = relationship(
        'Notification',
        lazy='joined',
        foreign_keys='Notification.owner_id',
        primaryjoin='NotificationSettings.owner_id == foreign(Notification.owner_id)',
        viewonly=True,
    )

    @hybrid_method
    def is_dm(self) -> bool:
        return self.channel_id == self.owner_id

    @hybrid_method
    def is_enabled(self) -> bool:
        return self.enabled

    @hybrid_method
    def count(self) -> int:
        return len(self.notifications)

    @hybrid_method
    def is_empty(self) -> bool:
        return self.count == 0

    @classmethod
    async def find_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls)
        stream = await session.stream_scalars(stmt)
        async for row in stream:
            yield row

    @classmethod
    async def find_by_owner_id(cls, session: AsyncSession, owner_id: int) -> Self | None:
        stmt = select(cls).where(cls.owner_id == owner_id)
        return await session.scalar(stmt)

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        owner_id: int,
        *,
        channel_id: int,
        mode: int,
        enabled: bool = False,
    ) -> Self:
        config = cls(owner_id=owner_id, channel_id=channel_id, mode=mode, enabled=enabled)
        session.add(config)
        await session.commit()
        return config

    async def update(
        self,
        session: AsyncSession,
        *,
        channel_id: int | None = None,
        mode: int | None = None,
        enabled: bool | None = None,
    ) -> Self:
        if channel_id is not None:
            self.channel_id = channel_id
        if mode is not None:
            self.mode = mode
        if enabled is not None:
            self.enabled = enabled
        await session.commit()
        new = await self.find_by_owner_id(session, self.owner_id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, notify_config: Self) -> None:
        stmt = delete(cls).where(cls.owner_id == notify_config.owner_id)
        await session.execute(stmt)
        await session.commit()
