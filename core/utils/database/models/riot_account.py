from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING, AsyncIterator, Optional

from dotenv import load_dotenv
from sqlalchemy import ForeignKey, String, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..encryption import FernetEngine
from .base import Base

if TYPE_CHECKING:
    from typing_extensions import Self

    from .user import User

# fmt: off
__all__ = (
    'RiotAccount',
)
# fmt: on

load_dotenv()

if 'CRYPTOGRAPHY_KEYS' not in os.environ:
    raise RuntimeError('CRYPTOGRAPHY_KEYS is not set in the environment')

fernet = FernetEngine(tuple(os.environ['CRYPTOGRAPHY_KEYS'].split(',')))


class RiotAccount(Base):
    __tablename__ = 'riot_accounts'

    id: Mapped[int] = mapped_column('id', primary_key=True, autoincrement=True)
    puuid: Mapped[str] = mapped_column('puuid', String(length=36), nullable=False)
    game_name: Mapped[Optional[str]] = mapped_column('name', String(length=16))
    tag_line: Mapped[Optional[str]] = mapped_column('tag', String(length=5))
    region: Mapped[str] = mapped_column('region', String(length=16), nullable=False)
    scope: Mapped[str] = mapped_column('scope', String(length=64), nullable=False)
    token_type: Mapped[str] = mapped_column('token_type', String(length=64), nullable=False)
    expires_at: Mapped[int] = mapped_column('expires_at', nullable=False)
    _id_token: Mapped[str] = mapped_column('id_token', String(length=4096), nullable=False)
    _access_token: Mapped[str] = mapped_column('access_token', String(length=4096), nullable=False)
    _entitlements_token: Mapped[str] = mapped_column('entitlements_token', String(length=4096), nullable=False)
    _ssid: Mapped[str] = mapped_column('ssid', String(length=4096), nullable=False)
    notify: Mapped[bool] = mapped_column('notify', nullable=False, default=False)
    incognito: Mapped[bool] = mapped_column('incognito', nullable=False, default=False)
    owner_id: Mapped[int] = mapped_column('owner_id', ForeignKey('users.id'), nullable=False)
    owner: Mapped[Optional[User]] = relationship('User', back_populates='riot_accounts', lazy='joined')
    created_at: Mapped[datetime.datetime] = mapped_column('created_at', nullable=False, default=datetime.datetime.utcnow)

    # NOTE: that there is no point in using a hybrid_property in this case, as your database can't encrypt and decrypt on the server side.
    @property
    def id_token(self) -> str:
        return fernet.decrypt(self._id_token.encode())

    @id_token.setter
    def id_token(self, value: str) -> None:
        self._id_token = fernet.encrypt(value.encode())

    @property
    def access_token(self) -> str:
        return fernet.decrypt(self._access_token.encode())

    @access_token.setter
    def access_token(self, value: str) -> None:
        self._access_token = fernet.encrypt(value.encode())

    @property
    def entitlements_token(self) -> str:
        return fernet.decrypt(self._entitlements_token.encode())

    @entitlements_token.setter
    def entitlements_token(self, value: str) -> None:
        self._entitlements_token = fernet.encrypt(value.encode())

    @property
    def ssid(self) -> str:
        return fernet.decrypt(self._ssid.encode())

    @ssid.setter
    def ssid(self, value: str) -> None:
        self._ssid = fernet.encrypt(value.encode())

    @hybrid_method
    def is_main_account(self) -> bool:
        if self.owner is None:
            return False
        if self.owner.main_riot_account_id is None:
            return False
        return self.owner.main_riot_account_id == self.id

    @classmethod
    async def read_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls)
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def read_all_by_owner_id(cls, session: AsyncSession, owner_id: int) -> AsyncIterator[Self]:
        stmt = select(cls).where(cls.owner_id == owner_id)
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def read_by_id(cls, session: AsyncSession, id: int) -> Optional[Self]:
        stmt = select(cls).where(cls.id == id)
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def read_by_puuid_and_owner_id(cls, session: AsyncSession, puuid: str, owner_id: int) -> Optional[Self]:
        stmt = select(cls).where(cls.puuid == puuid).where(cls.owner_id == owner_id)
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        owner_id: int,
        puuid: str,
        game_name: Optional[str],
        tag_line: Optional[str],
        region: str,
        scope: str,
        token_type: str,
        expires_at: int,
        id_token: str,
        access_token: str,
        entitlements_token: str,
        ssid: str,
        incognito: bool = False,
        notify: bool = False,
    ) -> Self:
        riot_account = cls(
            puuid=puuid,
            game_name=game_name,
            tag_line=tag_line,
            region=region,
            scope=scope,
            token_type=token_type,
            expires_at=expires_at,
            id_token=id_token,
            access_token=access_token,
            entitlements_token=entitlements_token,
            ssid=ssid,
            owner_id=owner_id,
            incognito=incognito,
            notify=notify,
        )
        session.add(riot_account)
        await session.flush()
        # To fetch the new object
        new = await cls.read_by_id(session, riot_account.id)
        if not new:
            raise RuntimeError()
        return riot_account

    async def update(
        self,
        session: AsyncSession,
        game_name: Optional[str] = None,
        tag_line: Optional[str] = None,
        region: Optional[str] = None,
        scope: Optional[str] = None,
        token_type: Optional[str] = None,
        expires_at: Optional[int] = None,
        id_token: Optional[str] = None,
        access_token: Optional[str] = None,
        entitlements_token: Optional[str] = None,
        ssid: Optional[str] = None,
        incognito: Optional[bool] = None,
        notify: Optional[bool] = None,
    ) -> Self:
        if game_name is not None:
            self.game_name = game_name
        if tag_line is not None:
            self.tag_line = tag_line
        if region is not None:
            self.region = region
        if scope is not None:
            self.scope = scope
        if token_type is not None:
            self.token_type = token_type
        if expires_at is not None:
            self.expires_at = expires_at
        if id_token is not None:
            self.id_token = id_token
        if access_token is not None:
            self.access_token = access_token
        if entitlements_token is not None:
            self.entitlements_token = entitlements_token
        if ssid is not None:
            self.ssid = ssid
        if incognito is not None:
            self.incognito = incognito
        if notify is not None:
            self.notify = notify
        await session.flush()
        # To fetch the new object
        new = await self.read_by_id(session, self.id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, riot_account: Self) -> None:
        await session.delete(riot_account)
        # stmt = delete(cls).where(cls.id == riot_account.id)
        await session.flush()

    @classmethod
    async def delete_all_by_owner_id(cls, session: AsyncSession, owner_id: int) -> None:
        stmt = delete(cls).where(cls.owner_id == owner_id)
        await session.execute(stmt)
        await session.flush()
