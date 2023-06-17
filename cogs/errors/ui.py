from __future__ import annotations

import contextlib
import io
import logging
import traceback
from typing import TYPE_CHECKING, Optional, Union

import discord
from discord import app_commands, ui
from discord.interactions import Interaction
from jishaku.paginators import PaginatorInterface, WrappedPaginator

import valorantx2 as valorantx
from core import errors
from core.i18n import I18n
from core.ui.embed import MiadEmbed
from core.utils import database

# from valorantx import valorant_api


if TYPE_CHECKING:
    from core.bot import LatteMaid

# inspired by shenhe_bot (seriaati) url: https://github.com/seriaati/shenhe_bot
# thanks for shenhe_bot <3

_ = I18n('Errors', __file__)

_log = logging.getLogger(__name__)


async def application_error_handler(
    interaction: Interaction[LatteMaid], error: Union[Exception, app_commands.AppCommandError]
):
    client = interaction.client
    locale = interaction.locale
    embed = build_error_handle_embed(interaction.user, error, locale)
    view = error_support_view(locale)

    with contextlib.suppress(discord.HTTPException):
        kwargs = {
            'embed': embed,
            'ephemeral': True,
            'view': view,
            'silent': True,
        }
        if interaction.response.is_done():
            await interaction.followup.send(**kwargs)
        else:
            await interaction.response.send_message(**kwargs)

        _log_error(interaction, error)

        if client.traceback_log is not None and embed.custom_id is not None and embed.custom_id == 'traceback':
            traceback_formatted = f"```py\n{traceback.format_exc()}\n```"
            if len(traceback_formatted) >= 1980:
                paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1980)
                result = str(traceback.format_exc())
                if len(result) <= 2000:
                    if result.strip() == '':
                        result = '\u200b'
                paginator.add_line(result)
                interface = PaginatorInterface(
                    client,
                    paginator,
                    owner=client.owner,
                    emoji='<:ThinkO_O:744344862521950268>',
                )
                client.loop.create_task(interface.send_to(client.traceback_log))
            else:
                fp = io.BytesIO(traceback.format_exc().encode('utf-8'))
                traceback_fp = discord.File(fp, filename='traceback.py')
                client.loop.create_task(client.traceback_log.send(content=client.owner.mention, file=traceback_fp))


def error_support_view(locale: discord.Locale) -> ui.View:
    view = ui.View()
    view.add_item(
        discord.ui.Button(
            label=_('Support Server', locale),
            url='https://discord.gg/4N2YkXbM',
            # emoji='',
        )
    )

    return view


def build_error_handle_embed(
    user: Optional[Union[discord.User, discord.Member]],
    error: Exception,
    locale: discord.Locale,
) -> MiadEmbed:
    # item = interaction.extras.get('item')
    # modal = interaction.extras.get('modal')

    embed = MiadEmbed().error()

    if isinstance(error, app_commands.errors.CommandInvokeError):
        error = error.original

    # https://discord.com/developers/docs/topics/opcodes-and-status-codes
    if isinstance(error, discord.errors.NotFound) and error.code in (
        10062,  # Unknown interaction
        10008,  # Unknown message
        10015,  # Unknown webhook
    ):
        embed.description = _('The message was deleted.', locale)
    elif isinstance(error, errors.ComponentOnCooldown):
        embed.description = _('You are on cooldown. Please try again in {seconds:.2f} seconds.', locale).format(
            seconds=error.retry_after
        )
    elif isinstance(error, errors.CheckFailure):
        # command = error.command
        # author = error.author
        embed.description = error.message
    elif isinstance(error, errors.RiotAuthError):
        embed.description = error.message
    elif isinstance(error, app_commands.errors.AppCommandError):
        if isinstance(error, app_commands.errors.CommandOnCooldown):
            embed.description = _('You are on cooldown. Please try again in {seconds:.2f} seconds.', locale).format(
                seconds=error.retry_after
            )
        # elif isinstance(error, (app_commands.errors.MissingRole, app_commands.errors.MissingAnyRole)):
        #     embed.description = _('You do not have the required role(s).', 0, locale)
        elif isinstance(error, app_commands.errors.CommandNotFound):
            embed.description = _(f'CommandNotFound', locale)
        elif isinstance(error, app_commands.errors.NoPrivateMessage):
            embed.description = _('UserAlreadyExists', locale)
    elif isinstance(error, database.errors.DatabaseBaseError):
        if isinstance(error, database.errors.UserAlreadyExists):
            embed.description = _('You are already registered.', locale)
        elif isinstance(error, database.errors.UserDoesNotExist):
            embed.description = _('You are not registered.', locale)
        elif isinstance(error, database.errors.BlacklistAlreadyExists):
            embed.description = _('You are already blacklisted.', locale)
        elif isinstance(error, database.errors.BlacklistDoesNotExist):
            embed.description = _('You are not blacklisted.', locale)
        elif isinstance(error, database.errors.RiotAccountAlreadyExists):
            embed.description = _('The Riot account is already registered.', locale)
        elif isinstance(error, database.errors.RiotAccountDoesNotExist):
            embed.description = _('The Riot account is not registered.', locale)
    elif isinstance(error, valorantx.errors.HTTPException):
        if isinstance(error, valorantx.errors.RiotAuthenticationError):
            embed.description = _('Riot Authentication Error', locale)
        elif isinstance(error, valorantx.errors.RiotRatelimitError):
            embed.description = _('Riot Rate Limit Error', locale)
        elif isinstance(
            error, (valorantx.errors.RiotUnknownResponseTypeError, valorantx.errors.RiotUnknownErrorTypeError)
        ):
            embed.description = _('Riot Unknown Error', locale)
        elif isinstance(error, valorantx.errors.BadRequest):  # status code 400
            embed.description = _(f'Bad Request from Riot API\n{error.text}', locale)
        elif isinstance(error, valorantx.errors.Forbidden):  # status code 403
            embed.description = _(f'Forbidden from Riot API \n{error.text}', locale)
        elif isinstance(error, valorantx.errors.NotFound):  # status code 404
            embed.description = _(f'Not Found from Riot API \n{error.text}', locale)
        elif isinstance(error, valorantx.errors.RateLimited):  # status code 429
            embed.description = _(f'You are rate limited from Riot API \n{error.text}', locale)
        elif isinstance(error, valorantx.errors.InternalServerError):  # status code 500
            embed.description = _(f'Internal Server Error from Riot API \n{error.text}', locale)
    else:
        embed.custom_id = 'traceback'

    icon_url = user.display_avatar.url if user else None
    embed.set_author(name=embed.author.name or 'Error', icon_url=icon_url)
    return embed


def _log_error(interaction: discord.Interaction[LatteMaid], error: Exception) -> None:
    command = interaction.command  # or interaction.extras.get('command')
    if command is not None:
        if command._has_any_error_handlers():
            return

        _log.error('exception in command %r', command.name, exc_info=error)
    else:
        _log.error('exception ', exc_info=error)

    # traceback_formatted = f"```py\n{traceback.format_exc()}\n```"
    # fp = io.BytesIO(traceback.format_exc().encode('utf-8'))
    # traceback_fp = discord.File(fp, filename='traceback.py')
    # if len(traceback_formatted) >= 1980:
    #     paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1980)
    #     result = str(traceback.format_exc())
    #     if len(result) <= 2000:
    #         if result.strip() == '':
    #             result = "\u200b"
    #     paginator.add_line(result)
    #     interface = PaginatorInterface(
    #         interaction.client, paginator, owner=interaction.user, emoji='<:ThinkO_O:744344862521950268>'
    #     )
    # await interaction.client.traceback_log.send(embed=embed, file=traceback_fp)
    # interaction.client.loop.create_task(interface.send_to(interaction.client.owner))
    # else:
    # embed.custom_id = 'traceback'
    # await self.bot.traceback_log.send(embed=embed, file=traceback_fp)


#     embed.description = f"```{type(e)}: {e}```"
#     embed.set_author(name=text_map.get(135, lang))
#     embed.set_thumbnail(url="https://i.imgur.com/Xi51hSe.gif")
