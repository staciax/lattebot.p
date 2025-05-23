from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING, AsyncIterator

from dotenv import load_dotenv
from sqlalchemy import ForeignKey, String, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
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
    puuid: Mapped[str] = mapped_column('puuid', String(length=36))
    game_name: Mapped[str | None] = mapped_column('name', String(length=16))
    tag_line: Mapped[str | None] = mapped_column('tag', String(length=5))
    region: Mapped[str] = mapped_column('region', String(length=16))
    scope: Mapped[str] = mapped_column('scope', String(length=64))
    token_type: Mapped[str] = mapped_column('token_type', String(length=64))
    expires_at: Mapped[int] = mapped_column('expires_at')
    _id_token: Mapped[str] = mapped_column('id_token', String(length=4096))
    _access_token: Mapped[str] = mapped_column('access_token', String(length=4096))
    _entitlements_token: Mapped[str] = mapped_column('entitlements_token', String(length=4096))
    _ssid: Mapped[str] = mapped_column('ssid', String(length=4096))
    notify: Mapped[bool] = mapped_column('notify', default=False)
    incognito: Mapped[bool] = mapped_column('incognito', default=False)
    owner_id: Mapped[int] = mapped_column('owner_id', ForeignKey('users.id'))
    owner: Mapped[User | None] = relationship('User', back_populates='riot_accounts', lazy='joined')
    created_at: Mapped[datetime.datetime] = mapped_column('created_at', default=datetime.datetime.utcnow)
    display_name: Mapped[str | None] = mapped_column('display_name', String(length=128))

    @hybrid_property
    def riot_id(self) -> str:
        return f'{self.game_name}#{self.tag_line}'

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
        if self.owner.riot_account_settings is None:
            return False
        return self.owner.riot_account_settings.current_account_id == self.id

    @classmethod
    async def find_all(cls, session: AsyncSession) -> AsyncIterator[Self]:
        stmt = select(cls)
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def find_all_by_owner_id(cls, session: AsyncSession, owner_id: int) -> AsyncIterator[Self]:
        stmt = select(cls).where(cls.owner_id == owner_id)
        stream = await session.stream_scalars(stmt.order_by(cls.id))
        async for row in stream:
            yield row

    @classmethod
    async def find_by_id(cls, session: AsyncSession, id: int) -> Self | None:
        stmt = select(cls).where(cls.id == id)
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def find_by_puuid_and_owner_id(cls, session: AsyncSession, puuid: str, owner_id: int) -> Self | None:
        stmt = select(cls).where(cls.puuid == puuid).where(cls.owner_id == owner_id)
        return await session.scalar(stmt.order_by(cls.id))

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        owner_id: int,
        puuid: str,
        game_name: str | None,
        tag_line: str | None,
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
        new = await cls.find_by_id(session, riot_account.id)
        if not new:
            raise RuntimeError()
        return riot_account

    async def update(
        self,
        session: AsyncSession,
        game_name: str | None = None,
        tag_line: str | None = None,
        region: str | None = None,
        scope: str | None = None,
        token_type: str | None = None,
        expires_at: int | None = None,
        id_token: str | None = None,
        access_token: str | None = None,
        entitlements_token: str | None = None,
        ssid: str | None = None,
        incognito: bool | None = None,
        notify: bool | None = None,
        display_name: str | None = None,
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
        if display_name is not None:
            self.display_name = display_name
        await session.flush()
        # To fetch the new object
        new = await self.find_by_id(session, self.id)
        if not new:
            raise RuntimeError()
        return new

    @classmethod
    async def delete(cls, session: AsyncSession, riot_account: Self) -> None:
        await session.delete(riot_account)
        await session.flush()

    @classmethod
    async def delete_all_by_owner_id(cls, session: AsyncSession, owner_id: int) -> None:
        stmt = delete(cls).where(cls.owner_id == owner_id)
        await session.execute(stmt)
        await session.flush()
