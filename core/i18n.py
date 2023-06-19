from __future__ import annotations

import contextlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Literal, Optional, TypedDict, TypeVar, Union

from discord import Locale
from discord.app_commands import Command, Group, Parameter
from discord.ext import commands

CogT = TypeVar('CogT', bound=commands.Cog)

# TODO: improve this

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


def get_path(
    cog_folder: Path,
    locale: str,
    folder: Literal['app_commands', 'strings', 'context_menus'],
    fmt: str = 'json',
) -> Path:
    return cog_folder / 'locales' / folder / f'{locale}.{fmt}'


def get_parameter_payload(
    parameter: Parameter,
    data: Optional[OptionLocalization] = None,
    *,
    merge: bool = True,
) -> OptionLocalization:
    payload: OptionLocalization = {
        'display_name': parameter.display_name,
        'description': parameter.description,
    }

    if len(parameter.choices) > 0:
        payload['choices'] = {str(choice.value): choice.name for choice in parameter.choices}

    if merge and data is not None:
        if 'display_name' in data and payload['display_name'] != data['display_name']:
            payload['display_name'] = data['display_name']

        if 'description' in data and payload['description'] != data['description']:
            payload['description'] = data['description']

        if len(parameter.choices) > 0:
            payload['choices'] = {}
            for choice in parameter.choices:
                if str(choice.value) in data.get('choices', {}):
                    payload['choices'][str(choice.value)] = data.get('choices', {})[str(choice.value)]
                else:
                    payload['choices'][str(choice.value)] = choice.name

    return payload


def get_app_command_payload(
    command: Union[Command, Group],
    data: Optional[AppCommandLocalization] = None,
    *,
    merge: bool = True,
) -> AppCommandLocalization:
    payload: AppCommandLocalization = {
        'name': command.name,
        'description': command.description,
    }

    if isinstance(command, Group):
        return payload

    if len(command.parameters) > 0:
        payload['options'] = {param.name: get_parameter_payload(param) for param in command.parameters}

    if merge and data is not None:
        if payload['name'] != data['name']:
            payload['name'] = data['name']

        if ('description' in data and 'description' in payload) and payload['description'] != data['description']:
            payload['description'] = data['description']

        if len(command.parameters) > 0:
            payload['options'] = {
                param.name: get_parameter_payload(param, data.get('options', {}).get(param.name, {}), merge=True)
                for param in command.parameters
            }

    return payload


class I18n:
    def __init__(
        self,
        name: str,
        file_location: Union[str, Path, os.PathLike],
        supported_locales: List[Locale] = [
            Locale.american_english,
            Locale.thai,
        ],
    ):
        self.cog_folder = Path(file_location).resolve().parent
        self._name = name
        self.supported_locales = supported_locales
        self.translations: Dict[str, Dict[str, str]] = {}
        self.app_translations: Dict[str, Dict[str, AppCommandLocalization]] = {}
        self.load()

    def load(self) -> None:
        self.load_translations()
        self.load_app_command_translations()

    def save(self) -> None:
        self.save_translations()
        self.save_app_command_translations()

    # strings

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

    def load_translations(self) -> None:
        for locale in Locale:
            locale_path = get_path(self.cog_folder, locale.value, 'strings')
            if not locale_path.exists():
                continue
            with contextlib.suppress(IOError, FileNotFoundError):
                with locale_path.open(encoding='utf-8') as file:
                    self.translations[locale.value] = json.load(file)

        _log.info(f'loaded {len(self.translations)} translations')

    def save_translations(self) -> None:
        for locale, translations in self.translations.items():
            locale_path = get_path(self.cog_folder, locale, 'strings')
            if not locale_path.parent.exists():
                locale_path.parent.mkdir(parents=True)
            with locale_path.open('w', encoding='utf-8') as file:
                json.dump(translations, file, indent=4, ensure_ascii=False)

    def get_translation(self, locale: str, key: str) -> Optional[str]:
        if locale not in self.translations:
            return None
        return self.translations[locale].get(key, None)

    def store_translation(
        self,
        locale: str,
        key: str,
        value: str,
        *,
        skip_if_exists: bool = False,
    ) -> None:
        if locale not in self.translations:
            self.translations[locale] = {}

        if skip_if_exists and key in self.translations[locale]:
            return

        self.translations[locale][key] = value

    # app commands

    def load_app_command_translations(self) -> None:
        for locale in self.supported_locales:
            locale_path = get_path(self.cog_folder, locale.value, 'app_commands')
            if not locale_path.exists():
                continue

            with locale_path.open('r', encoding='utf-8') as file:
                self.app_translations[locale.value] = json.load(file)

        _log.info(f'loaded {len(self.app_translations)} app command translations')

    def save_app_command_translations(self) -> None:
        for locale, translations in self.app_translations.items():
            locale_path = get_path(self.cog_folder, locale, 'app_commands')
            # if not locale_path.parent.exists():
            #     locale_path.parent.mkdir(parents=True)
            with locale_path.open('w', encoding='utf-8') as file:
                json.dump(dict(sorted(translations.items())), file, indent=4, ensure_ascii=False)

    def get_app_command_translation(
        self, locale: str, command: Union[Command, Group]
    ) -> Optional[AppCommandLocalization]:
        if locale not in self.app_translations:
            return None
        if command.name not in self.app_translations[locale]:
            return None
        return self.app_translations[locale][command.name]

    def store_app_command_translation(
        self,
        locale: str,
        command: Union[Command, Group],
        data: AppCommandLocalization,
    ) -> None:
        if locale not in self.app_translations:
            self.app_translations[locale] = {}

        self.app_translations[locale][command.qualified_name] = data

    def update_app_command_translation(
        self,
        locale: str,
        command: Union[Command, Group],
        data: AppCommandLocalization,
    ) -> None:
        if locale not in self.app_translations:
            self.app_translations[locale] = {}

        if command.qualified_name not in self.app_translations[locale]:
            return self.store_app_command_translation(locale, command, data)

        self.app_translations[locale][command.qualified_name].update(data)

    @staticmethod
    def invalidate_app_command_cache(i18n: I18n, cog: Union[type[commands.Cog], commands.Cog], locale: str) -> None:
        for attr in cog.__dict__.values():
            if isinstance(attr, (Command, Group)):
                i18n.update_app_command_translation(
                    locale,
                    attr,
                    get_app_command_payload(
                        attr,
                        data=i18n.get_app_command_translation(locale, attr),
                        merge=True,
                    ),
                )
            elif hasattr(attr, '__context_menu__'):
                print(attr.__context_menu__)


def cog_i18n(i18n: I18n):
    def decorator(cog_class: type[CogT]) -> type[CogT]:
        setattr(cog_class, '__i18n__', i18n)
        # for locale in i18n.supported_locales:
        #     i18n.invalidate_app_command_cache(i18n, cog_class, locale.value)
        # i18n.save()
        return cog_class

    return decorator
