from __future__ import annotations

import contextlib
import io
import json
import logging
import os
from contextvars import ContextVar

# from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

import discord
from discord import Locale

_log = logging.getLogger(__name__)


class Internationalization(TypedDict, total=False):
    strings: Dict[str, str]


_current_locale = ContextVar("_current_locale", default='en-US')


def get_locale() -> str:
    """
    Get locale in a current context.

    Returns
    -------
    str
        Current locale's language code with country code included, e.g. "en-US".
    """
    return str(_current_locale.get())


def get_locale_path(cog_folder: Path, locale: str, extension: str) -> Path:
    """
    Gets the folder path containing localization files.

    :param Path cog_folder:
        The cog folder that we want localizations for.
    :param str extension:
        Extension of localization files.
    :return:
        Path of possible localization file, it may not exist.
    """
    return cog_folder / 'locales' / '{}.{}'.format(locale, extension)


def _parse(translation_file: io.TextIOWrapper) -> Dict[str, str]:
    """
    Custom gettext parsing of translation files.

    Parameters
    ----------
    translation_file : io.TextIOWrapper
        An open text file containing translations.

    Returns
    -------
    Dict[str, str]
        A dict mapping the original strings to their translations. Empty
        translated strings are omitted.

    """
    step = None
    untranslated = ""
    translated = ""
    translations = {}
    locale = get_locale()

    translations[locale] = {}

    # for line in translation_file:
    #     line = line.strip()

    #     if line.startswith(MSGID):
    #         # New msgid
    #         if step is IN_MSGSTR and translated:
    #             # Store the last translation
    #             translations[locale][_unescape(untranslated)] = _unescape(translated)
    #         step = IN_MSGID
    #         untranslated = line[len(MSGID) : -1]
    #     elif line.startswith('"') and line.endswith('"'):
    #         if step is IN_MSGID:
    #             # Line continuing on from msgid
    #             untranslated += line[1:-1]
    #         elif step is IN_MSGSTR:
    #             # Line continuing on from msgstr
    #             translated += line[1:-1]
    #     elif line.startswith(MSGSTR):
    #         # New msgstr
    #         step = IN_MSGSTR
    #         translated = line[len(MSGSTR) : -1]

    # if step is IN_MSGSTR and translated:
    #     # Store the final translation
    #     translations[locale][_unescape(untranslated)] = _unescape(translated)
    return translations


_translators: List[I18n] = []


class I18n:
    # _localize_file = lru_cache(maxsize=1)(lambda self, locale: self._load_file(locale))
    __translations__: Dict[str, Any] = {str(locale): {} for locale in Locale}
    __strings__: Dict[discord.Locale, Dict[int, str]] = {locale: {} for locale in discord.Locale}
    # __user_locale__: Dict[int, discord.Locale] = {}

    def __init__(self, name: str, file_location: Union[str, Path, os.PathLike]):
        """
        Initializes an internationalization object.

        Parameters
        ----------
        name : str
            Your cog name.
        file_location : `str` or `pathlib.Path`
            This should always be ``__file__`` otherwise your localizations
            will not load.

        """
        self.cog_folder = Path(file_location).resolve().parent
        self.cog_name = name
        self.translations = {}

        _translators.append(self)
        self.load()

    def load(self) -> None:
        for locale in discord.Locale:
            locale_path = get_locale_path(self.cog_folder, locale.value, 'json')
            with contextlib.suppress(IOError, FileNotFoundError):
                with locale_path.open(encoding='utf-8') as file:
                    self._parse(locale.value, file)
        _log.info('loaded')

    def _parse(self, locale: str, translation_file: io.TextIOWrapper) -> None:
        payload = json.load(translation_file)
        data = payload.get('strings', {})
        self.translations[locale] = data
        # self.translations.update(data)
        # self.translations.update(_parse(translation_file))

    def unload(self) -> None:
        _log.info('unloaded')

    def __call__(
        self,
        untranslated: str,
        custom_id: Optional[int] = None,
        locale: Optional[Union[discord.Locale, str]] = None,
    ) -> str:
        print('cog name:', self.cog_name)
        print('translations:', self.translations)
        _log.info(f'call untranslated: {untranslated}, custom_id: {custom_id}, locale: {locale}')
        return untranslated

    # @staticmethod
    # def _load_file(path: str, locale: Locale) -> Internationalization:
    #     filename = '{}.json'.format(locale)
    #     fp = os.path.join(path, filename)
    #     try:
    #         with open(fp, 'r', encoding='utf-8') as f:
    #             data = json.load(f)
    #     except FileNotFoundError:
    #         return {}
    #     else:
    #         return data

    # @staticmethod
    # def _dump_file(path: str, locale: Locale, data: Dict[str, Any]) -> None:
    #     filename = '{}.json'.format(locale)
    #     fp = os.path.join(path, filename)
    #     with contextlib.suppress(IOError, FileNotFoundError):
    #         with open(fp, 'w', encoding='utf-8') as f:
    #             json.dump(data, f, indent=4, ensure_ascii=False)

    # def set_user_locale(self, interaction: discord.Interaction[LatteMaid]) -> None:
    #     I18n.__user_locale__[interaction.user.id] = interaction.locale

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
    #
    # locale_path = get_locale_path(self.cog_folder, "po")
    # with contextlib.suppress(IOError, FileNotFoundError):
    #     with locale_path.open(encoding="utf-8") as file:
    #         self._parse(file)

    # def _add_translation(self, untranslated, translated):
    #     untranslated = _unescape(untranslated)
    #     translated = _unescape(translated)
    #     if translated:
    #         self.translations[untranslated] = translated
    #
    # def _parse(self, key: str, translate: str):
    #     self._translations.update({key: translate})

    # def _get_string_path(self) -> str:
    #     return os.path.join(os.getcwd(), os.path.join('locales', 'string'))

    # @lru_cache(maxsize=31)
    # def _localize_file(self, locale: Locale) -> Internationalization:
    #     path = self._get_string_path()
    #     return self._load_file(path, locale)

    # def load_string_localize(self) -> None:
    #     for locale in discord.Locale:
    #         data = self._load_file(os.path.join(os.getcwd(), os.path.join('locale', 'string')), locale)
    #         strings = data.get('strings', {})
    #         for k, v in strings.items():
    #             I18n.__strings__[locale][int(k)] = v

    @classmethod
    def get_string(
        cls,
        untranslate: str,
        custom_id: Optional[int] = None,
        locale: Optional[Union[discord.Locale, str]] = None,
    ) -> str:
        if custom_id is None and locale is None:
            return untranslate

        # TODO: something to update in file

        locale = locale or discord.Locale.american_english

        if isinstance(locale, str):
            locale = discord.Locale(locale)

        locale_strings = I18n.__strings__.get(locale)
        if locale_strings is not None:
            return locale_strings.get(custom_id, untranslate)  # type: ignore
        return untranslate


from discord.app_commands import Command, Group


def cog_i18n(translator: I18n):
    """Get a class decorator to link the translator to this cog."""

    def decorator(cog_class: type):
        # cog_class.__translator__ = translator
        for name, attr in cog_class.__dict__.items():
            if isinstance(attr, (Command, Group)):  # ContextMenu:
                print(name, attr)
                # attr.translator = translator
                # setattr(cog_class, name, attr)
        return cog_class

    return decorator


_ = I18n.get_string
