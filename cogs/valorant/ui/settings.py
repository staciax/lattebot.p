from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord

from discord import ui
from core.i18n import I18n
from core.ui.views import ViewAuthor

if TYPE_CHECKING:
    from core.bot import LatteMaid

_ = I18n('valorant.ui.settings', Path(__file__).resolve().parent, read_only=True)


class SettingsView(ViewAuthor):
    def __init__(self, interaction: discord.Interaction[LatteMaid], *args: Any, **kwargs: Any) -> None:
        super().__init__(interaction, *args, **kwargs)
        self.fill_items()

    def fill_items(self) -> None:
        self.add_items(
            LanguageButton(locale=self.locale),
            NotificationButton(locale=self.locale),
        )

class LanguageButton(ui.Button['SettingsView']):

    def __init__(self, *, locale: discord.Locale, **kwargs: Any) -> None:
        super().__init__(
            label=_('button.language', locale=locale),
            **kwargs
        )
        self.locale = locale
    
    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        ...

class NotificationButton(ui.Button['SettingsView']):

    def __init__(self, *, locale: discord.Locale, **kwargs: Any) -> None:
        super().__init__(
            label=_('button.notification', locale=locale),
            **kwargs
        )
        self.locale = locale
    
    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        ...

class PreviousButton(ui.Button['SettingsView']):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            label='<',
            **kwargs
        )
    
    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        ...