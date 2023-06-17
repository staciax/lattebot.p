from __future__ import annotations

import contextlib
import io
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, TypeVar, Union

from discord import Locale

# from discord.app_commands import Command, Group
from discord.ext import commands

CogT = TypeVar('CogT', bound=commands.Cog)


_log = logging.getLogger(__name__)


def get_locale_string_path(cog_folder: Path, locale: str, fmt: str) -> Path:
    return cog_folder / 'locales' / 'strings' / f'{locale}.{fmt}'


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
            locale_path = get_locale_string_path(self.cog_folder, locale.value.lower(), 'json')
            with contextlib.suppress(IOError, FileNotFoundError):
                with locale_path.open(encoding='utf-8') as file:
                    self._parse(locale.value, file)
        _log.info('loaded')

    def unload(self) -> None:
        self.translations.clear()
        _log.info('unloaded')

    def reload(self) -> None:
        self.unload()
        self.load()

    def __call__(self, unique_id: str, locale: Optional[Union[Locale, str]] = None) -> str:
        if isinstance(unique_id, int):
            unique_id = str(unique_id)

        if locale is None:
            locale = Locale.american_english.value.lower()

        if isinstance(locale, Locale):
            locale = locale.value.lower()

        try:
            result = self.translations[locale][unique_id]
        except KeyError:
            # TODO: add to file
            _log.warning(f'no translation for {unique_id!r} in {locale}')
            return unique_id
        else:
            return result

    def get_text(self, unique_id: str, locale: Optional[Union[Locale, str]] = None) -> str:
        return self.__call__(unique_id, locale)

    def _parse(self, locale: str, translation_file: io.TextIOWrapper) -> None:
        self.translations[locale] = json.load(translation_file)
        # self.translations[locale].update(json.load(translation_file))

    async def _add_translation(self, key: str, value: str, locale: Optional[Union[Locale, str]] = None) -> None:
        if locale is None:
            locale = Locale.american_english.value.lower()

        if isinstance(locale, Locale):
            locale = locale.value.lower()

        self.translations[locale][key] = value


def cog_i18n(i18n: I18n):
    def decorator(cog_class: type[CogT]) -> type[CogT]:
        # cog_class.__translator__ = translator  # type: ignore
        # for name, attr in cog_class.__dict__.items():
        #     if isinstance(attr, (Command, Group)):
        #         attr.translator = translator  # type: ignore
        #         setattr(cog_class, name, attr)
        return cog_class

    return decorator
