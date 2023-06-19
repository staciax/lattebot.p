from __future__ import annotations

import logging
from itertools import chain
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from discord import Locale, app_commands
from discord.app_commands import (
    Choice,
    Command,
    ContextMenu,
    Group,
    Parameter,
    TranslationContextLocation as TCL,
    locale_str,
)

if TYPE_CHECKING:
    from discord.app_commands import TranslationContext

    from .bot import LatteMaid
    from .i18n import AppCommandLocalization, ContextMenuLocalization

    Localizable = Union[Command, Group, ContextMenu, Parameter, Choice]

_log = logging.getLogger(__name__)


class Translator(app_commands.Translator):
    __app_commands_i18n__: Dict[str, Dict[str, AppCommandLocalization]] = {}
    __context_menus_i18n__: Dict[str, Dict[str, ContextMenuLocalization]] = {}
    __string_i18n__: Dict[str, Dict[str, str]] = {}

    def __init__(self, bot: LatteMaid) -> None:
        super().__init__()
        self.bot: LatteMaid = bot
        self.__latest_command: Optional[Union[Command, Group, ContextMenu]] = None
        self.__latest_parameter: Optional[Parameter] = None

    async def load(self) -> None:
        _log.info('loaded')

    async def unload(self) -> None:
        _log.info('unloaded')

    async def translate(self, string: locale_str, locale: Locale, context: TranslationContext) -> Optional[str]:
        localizable: Localizable = context.data
        tcl: TCL = context.location

        if locale.value not in self.__app_commands_i18n__:
            return None

        if tcl != TCL.other:
            translations = self.__app_commands_i18n__[locale.value]
        elif isinstance(localizable, ContextMenu):
            translations = self.__context_menus_i18n__[locale.value]
        else:
            translations = {}

        localize_keys = self._build_localize_keys(tcl, localizable)

        def find_value_by_list_of_keys(fi18n: Any, keys: List[str]) -> Optional[str]:
            _string = fi18n.copy()
            for k in keys:
                try:
                    _string = _string[k]
                except KeyError:
                    return None

            if not isinstance(_string, str):
                _string = str(_string)

            return _string

        locale_string = find_value_by_list_of_keys(translations, localize_keys)
        if locale_string is None:
            _log.debug(f'not found: {string.message} for {locale.value} (tcl: {tcl})')
        print(locale, locale_string, localize_keys)
        return locale_string

    def _build_localize_keys(
        self,
        tcl: TCL,
        localizable: Localizable,
    ) -> List[str]:
        keys = []

        if tcl in [TCL.command_name, TCL.group_name] and isinstance(localizable, (Command, Group, ContextMenu)):
            keys.extend([localizable.qualified_name, 'name'])
            self.__latest_command = localizable

        elif tcl in [TCL.command_description, TCL.group_description] and isinstance(localizable, (Command, Group)):
            keys.extend([localizable.name, 'description'])

        elif tcl == TCL.parameter_name and isinstance(localizable, Parameter):
            keys.extend([localizable.command.name, 'options', localizable.name, 'display_name'])
            self.__latest_parameter = localizable

        elif tcl == TCL.parameter_description and isinstance(localizable, Parameter):
            keys.extend([localizable.command.name, 'options', localizable.name, 'description'])

        elif tcl == TCL.choice_name:
            if (
                self.__latest_command is not None
                and self.__latest_parameter is not None
                and isinstance(localizable, Choice)
            ):
                keys.extend(
                    [
                        self.__latest_command.name,
                        'options',
                        self.__latest_parameter.name,
                        'choices',
                        str(localizable.value),
                    ]
                )

        return keys

    @classmethod
    def get_string(cls, string: str, locale: Union[Locale, str]) -> Optional[str]:
        if isinstance(locale, Locale):
            locale = locale.value

        if locale not in cls.__string_i18n__:
            return None

        return cls.__string_i18n__[locale].get(string)

    # app_commands

    def update_app_commands_i18n(self, i18n: Dict[str, Dict[str, AppCommandLocalization]]) -> None:
        payload = {}

        for locale in chain(self.__app_commands_i18n__, i18n):
            payload[locale] = {
                **self.__app_commands_i18n__.get(locale, {}),
                **i18n.get(locale, {}),
            }

        self.__app_commands_i18n__ = payload

    def remove_app_commands_i18n(self, i18n: Dict[str, Dict[str, AppCommandLocalization]]) -> None:
        self.__app_commands_i18n__ = {
            locale: {
                name: localization
                for name, localization in self.__app_commands_i18n__[locale].items()
                if locale in i18n and name not in i18n[locale]
            }
            for locale in self.__app_commands_i18n__
        }


_ = Translator.get_string
