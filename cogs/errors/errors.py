from __future__ import annotations

import contextlib
import io
import logging
import traceback
from typing import TYPE_CHECKING

import discord
from discord import app_commands, ui
from jishaku.paginators import PaginatorInterface, WrappedPaginator

from core import database, errors
from core.cog import MaidCog
from core.i18n import I18n, cog_i18n
from core.ui.embed import MiadEmbed
from core.ui.views import BaseView
from core.utils.chat_formatting import code_block

if TYPE_CHECKING:
    from discord.ui import Item, Modal

    from core.bot import LatteMaid

_log = logging.getLogger(__name__)

_ = I18n('errors', __file__)

# NOTE: app error handler
# inspired by shenhe_bot (seriaati) url: https://github.com/seriaati/shenhe_bot
# thanks for shenhe_bot <3


async def application_error_handler(
    interaction: discord.Interaction[LatteMaid],
    error: Exception | app_commands.AppCommandError,
) -> None:
    locale = interaction.locale
    title, message = get_error_handle_message(error, locale)  # interaction.extras.get('embed')
    embed = get_error_handle_embed(interaction.user, title, message)

    view = guild_support_view(locale)

    with contextlib.suppress(discord.HTTPException):
        kwargs = {
            'embed': embed,
            'ephemeral': True,
            'view': view,
            'silent': True,
        }
        if interaction.response.is_done():
            message = await interaction.followup.send(**kwargs, wait=True)
            if not message.flags.ephemeral:
                # delete message after 120 seconds
                await message.delete(delay=120)
                # await message.edit(content='\u200b', embed=None, view=None)
                # await interaction.followup.send(**kwargs)

        else:
            # kwargs['delete_after'] = 60
            await interaction.response.send_message(**kwargs)


def guild_support_view(locale: discord.Locale) -> ui.View:
    view = BaseView().url_button(_('Support Server', locale), 'https://discord.gg/4N2YkXbM')
    return view


def get_error_handle_message(error: Exception, locale: discord.Locale) -> tuple[str, str]:
    # item = interaction.extras.get('item')
    # modal = interaction.extras.get('modal')

    title = _('Error', locale)
    message = _('An unknown error occurred.', locale)

    if isinstance(error, app_commands.errors.CommandInvokeError):
        error = error.original

    # https://discord.com/developers/docs/topics/opcodes-and-status-codes
    if isinstance(error, discord.errors.NotFound) and error.code in (
        10062,  # Unknown interaction
        10008,  # Unknown message
        10015,  # Unknown webhook
    ):
        title = _('Not Found', locale)
        message = _('The message was deleted.', locale)
    elif isinstance(error, errors.ComponentOnCooldown):
        title = _('Cooldown', locale)
        message = _('You are on cooldown. Please try again in {seconds:.2f} seconds.', locale).format(
            seconds=error.retry_after
        )
    elif isinstance(error, errors.UserInputError):
        message = error.message
    elif isinstance(error, errors.CheckFailure):
        title = _('Check Failure', locale)
        command = error.command
        author = error.author
        fmt = 'Only {author} can use this command. If you want to use it, use {command}'
        if isinstance(command, (app_commands.Command, app_commands.ContextMenu)) and author is not None:
            command_name = command.qualified_name
            model: discord.app_commands.AppCommand | None = command.extras.get('model', None)
            if model is not None:
                assert isinstance(model, discord.app_commands.AppCommand)
                command_name = model.mention
            message = fmt.format(author=author.mention, command=command_name)
        else:
            message = _('You are not allowed to use this.', locale)
    elif isinstance(error, app_commands.errors.AppCommandError):
        if isinstance(error, app_commands.errors.CommandOnCooldown):
            title = _('Cooldown', locale)
            message = _('You are on cooldown. Please try again in {seconds:.2f} seconds.', locale).format(
                seconds=error.retry_after
            )
        # elif isinstance(error, (app_commands.errors.MissingRole, app_commands.errors.MissingAnyRole)):
        #     message = _('You do not have the required role(s).', locale)
        elif isinstance(error, app_commands.errors.CommandNotFound):
            title = _('Command Not Found', locale)
            message = _('CommandNotFound', locale)
        elif isinstance(error, app_commands.errors.NoPrivateMessage):
            title = _('No Private Message', locale)
            message = _('UserAlreadyExists', locale)
    elif isinstance(error, database.errors.DatabaseBaseError):
        if isinstance(error, database.errors.UserAlreadyExists):
            title = _('User Already Exists', locale)
            message = _('You are already registered.', locale)
        elif isinstance(error, database.errors.UserDoesNotExist):
            title = _('User Does Not Exist', locale)
            message = _('You are not registered.', locale)
        elif isinstance(error, database.errors.BlacklistAlreadyExists):
            title = _('Blacklist Already Exists', locale)
            message = _('You are already blacklisted.', locale)
        elif isinstance(error, database.errors.BlacklistDoesNotExist):
            title = _('Blacklist Does Not Exist', locale)
            message = _('You are not blacklisted.', locale)
        elif isinstance(error, database.errors.RiotAccountAlreadyExists):
            title = _('Riot Account Already Exists', locale)
            message = _('The Riot account is already registered.', locale)
        elif isinstance(error, database.errors.RiotAccountDoesNotExist):
            title = _('Riot Account Does Not Exist', locale)
            message = _('The Riot account is not registered.', locale)

    return title, message


def get_error_handle_embed(
    user: discord.User | discord.Member | None,
    title: str,
    message: str,
) -> MiadEmbed:
    embed = MiadEmbed(description=message).error()
    icon_url = user.display_avatar.url if user else None
    embed.set_author(name=title, icon_url=icon_url)
    return embed


def _log_error(interaction: discord.Interaction[LatteMaid], error: Exception) -> None:
    command = interaction.command
    if command is not None:
        # if command._has_any_error_handlers():
        #     return
        _log.error('exception in command %r', command.name, exc_info=error)
    else:
        _log.error('exception ', exc_info=error)


@cog_i18n(_)
class Errors(MaidCog, name='errors'):
    """Developer commands"""

    def __init__(self, bot: LatteMaid) -> None:
        self.bot = bot

    async def send_traceback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        embed = MiadEmbed(timestamp=interaction.created_at).error()
        embed.set_author(name=f'{interaction.user} | {interaction.user.id}', icon_url=interaction.user.avatar)

        traceback_fmt = code_block(traceback.format_exc(), 'py')

        fp = io.BytesIO(traceback.format_exc().encode('utf-8'))
        traceback_fp = discord.File(fp, filename='traceback.py')

        if len(traceback_fmt) >= 1980:
            paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1980)
            result = str(traceback.format_exc())
            if len(result) <= 2000:
                if result.strip() == '':
                    result = '\u200b'
            paginator.add_line(result)
            interface = PaginatorInterface(self.bot, paginator, owner=self.bot.owner, emoji='<:ThinkO_O:744344862521950268>')
            await interface.send_to(self.bot.owner)

        if self.bot.traceback_log is not None:
            await self.bot.traceback_log.send(embed=embed, file=traceback_fp)

    @MaidCog.listener('on_app_command_error')
    async def on_app_command_error(
        self, interaction: discord.Interaction[LatteMaid], error: Exception | app_commands.errors.AppCommandError
    ) -> None:
        _log_error(interaction, error)
        await application_error_handler(interaction, error)
        # self.bot.loop.create_task(self.send_traceback(interaction))

    @MaidCog.listener('on_view_error')
    async def on_view_error(self, interaction: discord.Interaction[LatteMaid], error: Exception, item: Item) -> None:
        _log_error(interaction, error)
        interaction.extras['item'] = item
        await application_error_handler(interaction, error)

    @MaidCog.listener('on_modal_error')
    async def on_modal_error(self, interaction: discord.Interaction[LatteMaid], error: Exception, modal: Modal) -> None:
        _log_error(interaction, error)
        interaction.extras['modal'] = modal
        await application_error_handler(interaction, error)
