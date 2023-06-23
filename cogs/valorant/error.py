from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union

import discord
from discord import app_commands

import valorantx2 as valorantx
from core.errors import UserInputError
from core.i18n import I18n
from valorantx2 import valorant_api

from .abc import MixinMeta

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__name__)


_ = I18n('valorant.error', __file__, read_only=True)


class ErrorHandler(MixinMeta):
    async def cog_app_command_error(
        self,
        interaction: discord.Interaction[LatteMaid],
        error: Union[app_commands.AppCommandError, Exception],
    ) -> None:
        if isinstance(error, app_commands.errors.CommandInvokeError):
            error = error.original

        if not isinstance(error, (valorant_api.errors.ValorantAPIError, valorantx.errors.ValorantXError)):
            _log.exception('Unhandled exception in command %s:', interaction.command, exc_info=error)
            self.bot.dispatch('app_command_error', interaction, error)
            # return to global error handler
            return

        locale = interaction.locale
        # embed = Embed().error()

        message = _('An error occurred while processing the command.', locale)

        # valorant auth required error
        if isinstance(error, valorantx.RiotAuthRequired):
            message = _('You need to login to Riot account first.', locale)

        # auth error
        elif isinstance(error, valorantx.errors.RiotAuthError):
            if isinstance(error, valorantx.errors.RiotAuthenticationError):
                message = _('Invalid username or password.', locale)  # 'Invalid username or password.'
            elif isinstance(error, (valorantx.errors.RiotRatelimitError, valorantx.errors.RiotAuthRateLimitedError)):
                message = _('Riot Rate Limit Error', locale)
            elif isinstance(
                error, (valorantx.errors.RiotUnknownResponseTypeError, valorantx.errors.RiotUnknownErrorTypeError)
            ):
                message = _('Riot Unknown Error', locale)

        # valorant http error
        elif isinstance(error, valorantx.errors.InGameAPIError):
            # valorant in game api error
            if isinstance(error, valorantx.errors.BadRequest):
                message = _(f'Bad Request from Riot API\n{error.text}', locale)
            elif isinstance(error, valorantx.errors.Forbidden):
                message = _(f'Forbidden from Riot API \n{error.text}', locale)
            elif isinstance(error, valorantx.errors.NotFound):
                message = _(f'Not Found from Riot API \n{error.text}', locale)
            elif isinstance(error, valorantx.errors.RateLimited):
                message = _(f'You are rate limited from Riot API \n{error.text}', locale)
            elif isinstance(error, valorantx.errors.InternalServerError):
                message = _(f'Internal Server Error from Riot API \n{error.text}', locale)

        # valorant api error
        # elif isinstance(error, valorant_api.errors.ValorantAPIError):
        #     ...
        print(error, type(error))
        raise UserInputError(message)
