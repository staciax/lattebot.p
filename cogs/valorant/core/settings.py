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

    async def start(self) -> None:
        await self.interaction.response.send_message(
            content=_('message.settings'),
            view=self,
        )


class LanguageButton(ui.Button['SettingsView']):
    def __init__(self, *, locale: discord.Locale, **kwargs: Any) -> None:
        super().__init__(label=_('button.language', locale=locale), emoji='🌐', **kwargs)
        self.locale = locale

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        self.view.clear_items()
        self.view.add_items(PreviousButton(), LanguageSelect(support_locales=()))


class NotificationButton(ui.Button['SettingsView']):
    def __init__(self, *, locale: discord.Locale, **kwargs: Any) -> None:
        super().__init__(label=_('button.notification', locale=locale), emoji='🔔', **kwargs)
        self.locale = locale

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None: ...


class PreviousButton(ui.Button['SettingsView']):
    def __init__(self, row: int = 0, **kwargs: Any) -> None:
        super().__init__(label='<', row=row, **kwargs)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None: ...


class LanguageSelect(ui.Select['SettingsView']):
    def __init__(self, support_locales: tuple[discord.Locale, ...], **kwargs: Any) -> None:
        super().__init__(
            placeholder=_('select.language'), options=[discord.SelectOption(label='Automatic', value='auto')], **kwargs
        )
        self.support_locales = support_locales
        self.build_options()

    def build_options(self) -> None:
        for locale in self.support_locales:
            self.add_option(label=locale.name, value=locale.value)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        value = self.values[0]
        self.view.locale = discord.Locale(value)
        # user = interaction.user
        # bot = self.view.bot
        # await bot.db.update_user(user.id)
        await interaction.response.edit_message(view=self.view)
