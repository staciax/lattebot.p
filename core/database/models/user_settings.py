from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from sqlalchemy import ForeignKey, String, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_method
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

    user_id: Mapped[int] = mapped_column('user_id', ForeignKey('users.id'), nullable=False, primary_key=True, unique=True)
    user: Mapped[User] = relationship('User', lazy='joined')
    locale: Mapped[str | None] = mapped_column('locale', String(length=10), nullable=False)
