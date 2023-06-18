from __future__ import annotations

import contextlib
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, TypeVar, Union

from discord import Locale
from discord.app_commands import Choice, Command, ContextMenu, Group, Parameter
from discord.ext import commands

CogT = TypeVar('CogT', bound=commands.Cog)


_log = logging.getLogger(__name__)


class OptionLocalization(TypedDict, total=False):
    display_name: str
    description: str
    choices: Dict[Union[str, int, float], str]


class ContextMenuLocalization(TypedDict):
    name: str


class AppCommandLocalization(ContextMenuLocalization, total=False):
    description: str
    options: Dict[str, OptionLocalization]


def get_locale_path(
    cog_folder: Path,
    locale: str,
    fmt: str,
) -> Path:
    return cog_folder / 'locales' / 'app_commands' / f'{locale}.{fmt}'


class I18nApp:
    def __init__(self, name: str, file_location: Union[str, Path, os.PathLike]):
        self.cog_folder = Path(file_location).resolve().parent
        self.cog_name = name
        self.app_commands: List[Union[Command[Any, ..., Any], Group]] = []
        self.translations: Dict[str, AppCommandLocalization] = {}
        # self.app_commands: Dict[str, AppCommandLocalization] = {}
        # self.context_menus: Dict[str, ContextMenuLocalization] = {}
        # self.load()

    # def get_app_command(self, command: Union[Command, Group]) -> AppCommandLocalization:
    #     return self.app_commands[command.name]

    # def get_context_menu(self, context_menu: ContextMenu) -> ContextMenuLocalization:
    #     return self.context_menus[context_menu.name]

    def load(self) -> None:
        for locale in Locale:
            locale_path = get_locale_path(self.cog_folder, locale.value.lower(), 'json')
            with contextlib.suppress(IOError, FileNotFoundError):
                with locale_path.open(encoding='utf-8') as file:
                    self._parse(locale.value, file)

    def save_to_file(self, locale: str, data: Dict[str, AppCommandLocalization]) -> None:
        locale_path = get_locale_path(self.cog_folder, locale, 'json')
        with locale_path.open('w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        _log.info(f'saved {locale_path}')

    def _parse(self, locale: str, translation_file: io.TextIOWrapper) -> None:
        if locale not in self.translations:
            self.translations[locale] = json.load(translation_file)

        # payload = json.load(translation_file)
        # self.translations[locale].update(payload)

    def get_parameter_payload(self, parameter: Parameter) -> OptionLocalization:
        payload: OptionLocalization = {
            'display_name': parameter.display_name,
            'description': parameter.description,
        }
        if len(parameter.choices) > 0:
            payload['choices'] = {choice.value: choice.name for choice in parameter.choices}
        return payload

    def get_app_command_payload(self, command: Union[Command, Group]) -> Any:
        payload: AppCommandLocalization = {
            'name': command.name,
            'description': command.description,
        }
        if isinstance(command, Group):
            return payload
        if len(command.parameters) > 0:
            payload['options'] = {param.name: self.get_parameter_payload(param) for param in command.parameters}
        return payload

    def validate_payload(
        self,
        original: AppCommandLocalization,
        from_file: AppCommandLocalization,
        replace: bool = False,
    ) -> AppCommandLocalization:
        # remove useless keys

        for key in list(from_file.keys()):
            if key not in original:
                del from_file[key]

        return from_file

    # def unload(self) -> None:
    #     self.translations.clear()
    #     _log.info('unloaded')

    # def reload(self) -> None:
    #     self.unload()


def cog_app_i18n(i18n: I18nApp):
    def decorator(cog_class: type[CogT]) -> type[CogT]:
        payload: Dict[str, AppCommandLocalization] = {}
        for attr in cog_class.__dict__.values():
            if isinstance(attr, (Command, Group)):
                payload[attr.name] = i18n.get_app_command_payload(attr)

        return cog_class

    return decorator
