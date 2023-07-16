from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from sqlalchemy import ForeignKey, String, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import Mapped, mapped_column, relationship  # foreign, _

from .base import Base

if TYPE_CHECKING:
    from typing_extensions import Self

    from .riot_account import RiotAccount
    from .user import User

# fmt: off
__all__ = (
    'RiotAccountSettings',
)
# fmt: on


class RiotAccountSettings(Base):
    __tablename__ = 'riot_account_settings'

    user_id: Mapped[int] = mapped_column('user_id', ForeignKey('users.id'), nullable=False, primary_key=True, unique=True)
    user: Mapped[User] = relationship('User', lazy='joined')
    current_account: Mapped[RiotAccount | None] = relationship('RiotAccount', lazy='joined', viewonly=True)
    current_account_id: Mapped[int | None] = mapped_column(
        'current_account_id',
        ForeignKey('riot_accounts.id'),
        nullable=True,
    )
