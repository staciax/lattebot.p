from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord

from core.i18n import I18n
from core.ui.views import ViewAuthor

if TYPE_CHECKING:
    from core.bot import LatteMaid

_ = I18n('valorant.ui.settings', Path(__file__).resolve().parent, read_only=True)


class SettingsView(ViewAuthor):
    def __init__(self, interaction: discord.Interaction[LatteMaid], *args: Any, **kwargs: Any) -> None:
        super().__init__(interaction, *args, **kwargs)

    async def _init(self) -> None:
        ...

    async def start(self) -> None:
        ...
