from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union

import discord
from discord import app_commands

import valorantx2 as valorantx

# from core.errors import UserInputError
from core.i18n import I18n

# from core.ui.embed import MiadEmbed as Embed
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
        locale = interaction.locale
        # embed = Embed().error()

        message = _('An error occurred while processing the command.', locale)

        if isinstance(error, app_commands.errors.CommandInvokeError):
            error = error.original

        if not isinstance(error, (valorant_api.errors.ValorantAPIError, valorantx.errors.ValorantXError)):
            self.bot.dispatch('app_command_error', interaction, error)
            # return to global error handler
            return

        # valorant http error
        if isinstance(error, valorantx.errors.InGameAPIError):
            # valorant in game api error
            if isinstance(error, valorantx.errors.BadRequest):  # status code 400
                message = _(f'Bad Request from Riot API\n{error.text}', locale)
            elif isinstance(error, valorantx.errors.Forbidden):  # status code 403
                message = _(f'Forbidden from Riot API \n{error.text}', locale)
            elif isinstance(error, valorantx.errors.NotFound):  # status code 404
                message = _(f'Not Found from Riot API \n{error.text}', locale)
            elif isinstance(error, valorantx.errors.RateLimited):  # status code 429
                message = _(f'You are rate limited from Riot API \n{error.text}', locale)
            elif isinstance(error, valorantx.errors.InternalServerError):  # status code 500
                message = _(f'Internal Server Error from Riot API \n{error.text}', locale)

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

        # valorant api error
        # elif isinstance(error, valorant_api.errors.ValorantAPIError):
        #     ...

        # raise UserInputError(message)

        # interaction.extras['embed'] = embed
        self.bot.dispatch('app_command_error', interaction, error)
