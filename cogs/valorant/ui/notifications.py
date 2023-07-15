from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord import ui

from core.i18n import I18n
from core.ui.views import ViewAuthor

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from core.database.models import User

_log = logging.getLogger(__name__)

_ = I18n('valorant.ui.notifications', Path(__file__).resolve().parent, read_only=True)


class NotifyView(ViewAuthor):
    user: User

    def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__(interaction)

    async def _init(self) -> None:
        user = await self.bot.db.get_user(self.author.id)
        if user is None:
            # await self.bot.db.create_user(self.author.id, locale=self.locale)
            raise RuntimeError('User not found')

        if not len(user.riot_accounts):
            raise RuntimeError('User has no riot accounts')

        self.user = user

    async def start(self) -> None:
        await self._init()
        self.add_buttons()

    def add_buttons(self) -> None:
        self.clear_items()
        self.add_item(StoreNotify(label='Store'))
        self.add_item(AccessorieNotify(label='Accessorie'))
        self.add_item(PatchNoteNotify(label='Patch Note'))


class StoreNotify(ui.Button['NotifyView']):
    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        ...


class AccessorieNotify(ui.Button['NotifyView']):
    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        ...


class PatchNoteNotify(ui.Button['NotifyView']):
    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        ...
