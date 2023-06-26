from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypeVar, Union

from discord import Locale

if TYPE_CHECKING:
    from discord.ext import commands

    CogT = TypeVar('CogT', bound=commands.Cog)

_log = logging.getLogger(__name__)


def get_path(
    cog_folder: Path,
    locale: str,
    fmt: str = 'json',
) -> Path:
    return cog_folder / 'locales' / 'strings' / '{locale}.{fmt}'.format(locale=locale, fmt=fmt)


class I18n:
    def __init__(
        self,
        name: str,
        file_location: Union[str, Path, os.PathLike],
        supported_locales: List[Locale] = [
            Locale.american_english,
            Locale.thai,
        ],
        *,
        read_only: bool = False,
        load_later: bool = False,
    ) -> None:
        self.cog_folder: Path = Path(file_location).resolve().parent
        self.cog_name: str = name
        self.supported_locales: List[Locale] = supported_locales
        self.read_only: bool = read_only
        self.loop = asyncio.get_event_loop()
        self.lock = asyncio.Lock()
        self._data: Dict[str, Dict[str, Dict[str, str]]] = {}
        if load_later:
            self.loop.create_task(self.load())
        else:
            self._load()

    async def load(self) -> None:
        async with self.lock:
            await self.loop.run_in_executor(None, self._load)

    def _load(self) -> None:
        for locale in self.supported_locales:
            self.load_from_file(locale.value)
        if not self.read_only:
            self.loop.create_task(self.save())
        _log.info(f'loaded i18n for cogs.{self.cog_name} ')

    def load_from_file(self, locale: str) -> None:
        locale_path = get_path(self.cog_folder, locale)
        if not locale_path.exists():
            self._data[locale] = {}

        with contextlib.suppress(IOError, FileNotFoundError):
            with locale_path.open(encoding='utf-8') as file:
                self._data[locale] = json.load(file)

    async def save(self) -> None:
        for locale in self._data:
            async with self.lock:
                await self.loop.run_in_executor(None, self._dump, locale)
        _log.debug(f'saved i18n for {self.cog_name}')

    def _dump(self, locale: str) -> None:
        if locale not in self._data:
            self._data[locale] = {}

        locale_path = get_path(self.cog_folder, locale)
        with contextlib.suppress(IOError, FileExistsError):
            if not locale_path.parent.exists():
                locale_path.parent.mkdir(parents=True)
                _log.debug(f'created {locale_path.parent}')

        data = self._data[locale]

        with locale_path.open('w', encoding='utf-8') as file:
            json.dump(data.copy(), file, indent=4, ensure_ascii=False)
            _log.debug(f'saved i18n for {self.cog_name} in {locale}')

    def get_locale(self, locale: str, default: Any = None) -> Optional[Union[Dict[str, str], Any]]:
        """Retrieves a locale entry."""
        return self._data.get(locale, default)

    async def remove_locale(self, locale: str) -> None:
        """Removes a locale."""
        self._data.pop(locale, None)
        await self.save()

    async def add_locale(self, locale: str) -> None:
        """Adds a locale."""
        if locale in self._data:
            return
        self._data[locale] = {}
        await self.save()

    def get_text(self, key: str, locale: Union[Locale, str]) -> Union[str, Optional[str]]:
        if isinstance(locale, Locale):
            locale = locale.value

        locale_data = self.get_locale(locale)
        if locale_data is None:
            return None

        return locale_data.get(key)

    def __call__(self, key: str, locale: Optional[Union[Locale, str]] = None) -> str:
        if locale is None:
            locale = Locale.american_english

        if isinstance(locale, Locale):
            locale = locale.value

        # default to american english
        if locale not in self._data:
            locale = Locale.american_english

        text = self.get_text(key, locale)
        if text is None:
            _log.warning(f'found key:{key!r} locale:{locale}')
            return key

        _log.debug(f'returning {text!r} for {key!r} in {locale}')
        return text

    def __contains__(self, locale: Union[Locale, str]) -> bool:
        if isinstance(locale, Locale):
            locale = locale.value
        return locale in self._data


def cog_i18n(i18n: I18n):
    def decorator(cog_class: type[CogT]) -> type[CogT]:
        setattr(cog_class, '__i18n__', i18n)
        return cog_class

    return decorator
