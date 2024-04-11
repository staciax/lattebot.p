from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands

import valorantx2 as valorantx
from core.i18n import I18n
from valorantx2 import valorant_api

from .abc import MixinMeta

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__name__)


_ = I18n('valorant.error', __file__, read_only=True)


class ValorantError(Exception):
    """Base exception class for valorant cog."""


class RiotAuthAlreadyLinked(ValorantError):
    """Raised when a user has already linked a Riot account."""

    pass


class RiotAuthNotLinked(ValorantError):
    """Raised when a user has not linked a Riot account."""

    pass


class RiotAuthMaxLimitReached(ValorantError):
    """Raised when a user has reached the max limit of Riot accounts."""

    pass


class RiotAuthMultiFactorTimeout(ValorantError):
    """Raised when a user has not entered the multi factor code in time."""

    pass


class RiotAuthNotFound(ValorantError):
    """Raised when riot auth is not found."""

    pass


class RiotAuthUnknownError(ValorantError):
    """Raised when an unknown error occurred while authenticating."""

    def __init__(self, original: Exception) -> None:
        self.original = original
        super().__init__(f'Unknown error: {original}')


class ErrorHandler(MixinMeta):
    async def cog_app_command_error(
        self, interaction: discord.Interaction[LatteMaid], error: app_commands.AppCommandError | Exception
    ) -> None:
        if isinstance(error, app_commands.errors.CommandInvokeError):
            error = error.original

        if not isinstance(
            error, (valorant_api.errors.ValorantAPIError, valorantx.errors.ValorantXError, ValorantError)
        ):
            _log.exception('Unhandled exception in command %s:', interaction.command, exc_info=error)
            self.bot.dispatch('app_command_error', interaction, error)
            # return to global error handler
            return

        locale = interaction.locale

        title = _('Valorant Error', locale)
        message = _('An error occurred while processing the command.', locale)

        # valorant auth required error
        if isinstance(error, valorantx.RiotAuthRequired):
            message = _('You need to login to Riot account first.', locale)

        # auth error
        elif isinstance(error, valorantx.errors.RiotAuthError):
            title = _('Riot Authentication Error', locale)
            if isinstance(error, valorantx.errors.RiotAuthenticationError):
                message = _('Invalid username or password.', locale)
            elif isinstance(error, valorantx.errors.RiotAuthMultiFactorInvalidCode):
                message = _('Invalid multi factor code: ||{code}||'.format(code=error.mfa_code), locale)
            elif isinstance(error, (valorantx.errors.RiotRatelimitError, valorantx.errors.RiotAuthRateLimitedError)):
                message = _('Riot Rate Limit Error', locale)
            elif isinstance(
                error, (valorantx.errors.RiotUnknownResponseTypeError, valorantx.errors.RiotUnknownErrorTypeError)
            ):
                message = _('Riot Unknown Error', locale)

        # valorant http error
        elif isinstance(error, valorantx.errors.InGameAPIError):
            title = _('Valorant In Game API Error', locale)
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

        elif isinstance(error, ValorantError):
            title = _('Valorant Error', locale)
            if isinstance(error, RiotAuthAlreadyLinked):
                message = _('You have already linked a Riot account.', locale)
            elif isinstance(error, RiotAuthNotLinked):
                message = _('You have not linked a Riot account.', locale)
            elif isinstance(error, RiotAuthMaxLimitReached):
                message = _('You have reached the max limit of Riot accounts.', locale)
            elif isinstance(error, RiotAuthMultiFactorTimeout):
                message = _('Multi factor timeout.', locale)

            elif isinstance(error, RiotAuthUnknownError):
                message = _('Unknown error occurred while processing the command.', locale)

        # interaction.extras['error'] = {'title': title, 'message': message}
        self.bot.dispatch('app_command_error', interaction, error)
