from __future__ import annotations

import contextlib
import io
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, TypeVar, Union

from discord import Locale
from discord.app_commands import Command, Group
from discord.ext import commands

CogT = TypeVar('CogT', bound=commands.Cog)


_log = logging.getLogger(__name__)


def get_locale_path(
    cog_folder: Path,
    locale: str,
    fmt: str,
) -> Path:
    return cog_folder / 'locales' / 'strings' / f'{locale}.{fmt}'


# def get_locale_app_command_path(cog_folder: Path, locale: str, fmt: str) -> Path:
#     return cog_folder / 'locales' / 'app_commands' / f'{locale}.{fmt}'


_translators: List[I18n] = []


class I18n:
    def __init__(self, name: str, file_location: Union[str, Path, os.PathLike]):
        self.cog_folder = Path(file_location).resolve().parent
        self.cog_name = name
        self.translations: Dict[str, Dict[str, str]] = {}
        _translators.append(self)
        self.load()

    def load(self) -> None:
        for locale in Locale:
            locale_string_path = get_locale_path(self.cog_folder, locale.value.lower(), 'json')
            with contextlib.suppress(IOError, FileNotFoundError):
                with locale_string_path.open(encoding='utf-8') as file:
                    self._parse(locale.value, file)

        _log.info('loaded')

    def unload(self) -> None:
        self.translations.clear()
        _log.info('unloaded')

    def reload(self) -> None:
        self.unload()
        self.load()

    def __call__(self, key: str, locale: Optional[Union[Locale, str]] = None) -> str:
        if isinstance(key, int):
            key = str(key)

        if locale is None:
            locale = Locale.american_english.value.lower()

        if isinstance(locale, Locale):
            locale = locale.value.lower()

        try:
            result = self.translations[locale][key]
        except KeyError:
            # TODO: add to file
            _log.warning(f'no translation for {key!r} in {locale}')
            return key
        else:
            return result

    def get_text(self, key: str, locale: Optional[Union[Locale, str]] = None) -> str:
        return self.__call__(key, locale)

    def _parse(self, locale: str, translation_file: io.TextIOWrapper) -> None:
        if locale not in self.translations:
            self.translations[locale] = {}

        payload = json.load(translation_file)
        self.translations[locale].update(payload)

    async def _add_translation(self, key: str, value: str, locale: Optional[Union[Locale, str]] = None) -> None:
        if locale is None:
            locale = Locale.american_english.value.lower()

        if isinstance(locale, Locale):
            locale = locale.value.lower()

        if locale not in self.translations:
            self.translations[locale] = {}

        self.translations[locale][key] = value


# def cog_i18n(i18n: I18n):
#     def decorator(cog_class: type[CogT]) -> type[CogT]:
#         for name, attr in cog_class.__dict__.items():
#             if isinstance(attr, (Command, Group)):
#                 ...
#         return cog_class

#     return decorator


def cog_i18n(i18n: I18n):
    def decorator(cog_class: type[CogT]) -> type[CogT]:
        setattr(cog_class, '__translator__', i18n)
        for name, attr in cog_class.__dict__.items():
            if isinstance(attr, (Command, Group)):
                setattr(attr, '__i18n__', i18n)
                setattr(cog_class, name, attr)

            # if context_values := getattr(attr, '__context_menu__', None):
            #     print(context_values)
        return cog_class

    return decorator
