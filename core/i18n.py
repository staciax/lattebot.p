from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, TypedDict

import discord
from discord import Locale

if TYPE_CHECKING:
    from .bot import LatteMaid


_log = logging.getLogger(__file__)


class Internationalization(TypedDict, total=False):
    strings: Dict[str, str]


_translators: List[I18n] = []


class I18n:
    # _localize_file = lru_cache(maxsize=1)(lambda self, locale: self._load_file(locale))
    __current_locale__: discord.Locale = discord.Locale.american_english
    __translations__: Dict[str, Any] = {str(locale): {} for locale in Locale}
    __strings__: Dict[discord.Locale, Dict[str, Any]] = {locale: {} for locale in discord.Locale}
    __user_locale__: Dict[int, discord.Locale] = {}

    def __init__(self, bot: LatteMaid) -> None:
        super().__init__()
        self.bot: LatteMaid = bot
        _translators.append(self)

    # async def load(self) -> None:
    #     _log.info('loaded')

    # async def unload(self) -> None:
    #     _log.info('unloaded')

    # def __call__(self, untranslated: str) -> locale_str:
    #     return locale_str(untranslated)

    @staticmethod
    def _load_file(path: str, locale: Locale) -> Internationalization:
        filename = '{}.json'.format(locale)
        fp = os.path.join(path, filename)
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            return {}
        else:
            return data

    @staticmethod
    def _dump_file(path: str, locale: Locale, data: Dict[str, Any]) -> None:
        filename = '{}.json'.format(locale)
        fp = os.path.join(path, filename)
        try:
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except FileNotFoundError:
            _log.warning(f'File {fp!r} not found')

    def set_locale(self, interaction: discord.Interaction) -> None:
        I18n.__user_locale__[interaction.user.id] = interaction.locale

    # def load_translations(self):
    #     """
    #     Loads the current translations.
    #     """
    #     locale = get_locale()
    #     if locale.lower() == "en-us":
    #         return
    #     if locale in self.translations:
    #         # Locales cannot be loaded twice as they have an entry in
    #         # self.translations
    #         return
    #     #
    #     # locale_path = get_locale_path(self.cog_folder, "po")
    #     # with contextlib.suppress(IOError, FileNotFoundError):
    #     #     with locale_path.open(encoding="utf-8") as file:
    #     #         self._parse(file)

    #
    # def _add_translation(self, untranslated, translated):
    #     untranslated = _unescape(untranslated)
    #     translated = _unescape(translated)
    #     if translated:
    #         self.translations[untranslated] = translated
    #
    # def _parse(self, key: str, translate: str):
    #     self._translations.update({key: translate})

    def _get_string_path(self) -> str:
        return os.path.join(os.getcwd(), os.path.join('locales', 'string'))

    @lru_cache(maxsize=31)
    def _localize_file(self, locale: Locale) -> Internationalization:
        path = self._get_string_path()
        return self._load_file(path, locale)

    def load_string_localize(self) -> None:
        for locale in discord.Locale:
            data = self._load_file(os.path.join(os.getcwd(), os.path.join('locale', 'string')), locale)
            strings = data.get('strings', {})
            for k, v in strings.items():
                I18n.__strings__[locale][k] = v

    @classmethod
    def get_string(
        cls,
        untranslate: str,
        locale: Optional[discord.Locale] = None,
        *,
        custom_id: Optional[str] = None,
    ) -> str:
        print(untranslate)
        locale = locale or cls.__current_locale__
        key = custom_id or untranslate
        return cls.__strings__[locale].get(key, untranslate)


_: Callable[[str], str] = I18n.get_string
