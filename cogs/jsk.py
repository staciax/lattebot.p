from __future__ import annotations

import inspect
import io
import logging
import pathlib
from typing import TYPE_CHECKING, Any, Callable  # noqa: UP035

import discord
from discord import app_commands
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import bot_has_permissions
from discord.ext import commands
from discord.ext.commands.view import StringView
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check
from jishaku.repl import AsyncCodeExecutor, get_var_dict_from_ctx  # type: ignore

from core.checks import owner_only
from core.errors import UserInputError

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__file__)

# https://github.com/Gorialis/jishaku


class Jishaku(*OPTIONAL_FEATURES, *STANDARD_FEATURES, name='jishaku'):
    bot: LatteMaid

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.ctx_msg_jsk_py = app_commands.ContextMenu(
            name=_T('Python'),
            callback=self.ctx_message_jishaku_python,
            guild_ids=[
                self.bot.support_guild_id,
                1042503061454729289,  # EMOJI ABILITY 2
                1042502960921452734,  # EMOJI ABILITY 1
                1043965050630705182,  # EMOJI TIER
                1042501718958669965,  # EMOJI AGENT
                1042809126624964651,  # EMOJI MATCH
            ],
        )
        self.ctx_msg_jsk_py.on_error = self.cog_app_command_error
        setattr(self.ctx_msg_jsk_py, '__binding__', self)  # noqa: B010

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.ctx_msg_jsk_py)
        await super().cog_load()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_msg_jsk_py.name, type=self.ctx_msg_jsk_py.type)
        await super().cog_unload()

    async def cog_app_command_error(
        self, interaction: discord.Interaction[LatteMaid], error: app_commands.AppCommandError
    ) -> None:
        interaction.client.dispatch('app_command_error', interaction, error)

    async def cog_check(self, ctx: commands.Context[LatteMaid]):
        if not await ctx.bot.is_owner(ctx.author):
            raise commands.NotOwner('You must own this bot to use Jishaku.')
        return True

    async def interaction_check(self, interaction: discord.Interaction[LatteMaid]) -> bool:
        if not await interaction.client.is_owner(interaction.user):
            raise UserInputError('You must own this bot to use Jishaku.')
        return super().interaction_check(interaction)

    @Feature.Command(name='jishaku', aliases=['jsk'], invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: commands.Context[LatteMaid]) -> None:
        """
        The Jishaku debug and diagnostic commands.

        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """
        embed = discord.Embed(
            title='Jishaku',
            description=f'Jishaku is a debug and diagnostic cog for **{self.bot.user}**.',
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, silent=True)

    @Feature.Command(parent='jsk', name='source', aliases=['src'])
    async def jsk_source(self, ctx: commands.Context[LatteMaid], *, command_name: str) -> None:
        """
        Displays the source code for an app command.
        """

        command = self.bot.get_command(command_name) or self.bot.tree.get_command(command_name)
        if not command:
            await ctx.send(f"Couldn't find command `{command_name}`.")
            return

        try:
            source_lines, _ = inspect.getsourcelines(command.callback)  # type: ignore
        except (TypeError, OSError):
            await ctx.send(f'Was unable to retrieve the source for `{command}` for some reason.')
            return

        filename = 'source.py'

        try:
            filename = pathlib.Path(inspect.getfile(command.callback)).name  # type: ignore
        except (TypeError, OSError):
            pass

        # getsourcelines for some reason returns WITH line endings
        source_text = ''.join(source_lines)

        if use_file_check(ctx, len(source_text)):  # File "full content" preview limit
            await ctx.send(file=discord.File(filename=filename, fp=io.BytesIO(source_text.encode('utf-8'))))
        else:
            paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1900)

            paginator.add_line(source_text.replace('```', '``\N{ZERO WIDTH SPACE}`'))

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            await interface.send_to(ctx)

    @Feature.Command(parent='jsk', name='py', aliases=['python'])
    async def jsk_python(self, ctx: commands.Context[LatteMaid], *, argument: codeblock_converter):  # type: ignore
        if TYPE_CHECKING:
            argument: Codeblock = argument

        arg_dict = get_var_dict_from_ctx(ctx, '')
        arg_dict.update(get_var_dict_from_ctx(ctx, '_'))
        arg_dict['_'] = self.last_result

        scope = self.scope

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict)
                    async for send, result in AsyncSender(executor):  # type: ignore
                        send: Callable[..., None]
                        result: Any

                        if result is None:
                            continue

                        self.last_result = result

                        send(await self.jsk_python_result_handling(ctx, result))

        finally:
            scope.clear_intersection(arg_dict)

    @app_commands.command(name=_T('jsk'))
    @app_commands.describe(sub=_T('Sub command of jsk'), args=_T('Arguments of jsk'))
    @app_commands.rename(sub=_T('sub'), args=_T('args'))
    @app_commands.default_permissions(administrator=True)
    @bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    @owner_only()
    async def jishaku_app(
        self,
        interaction: discord.Interaction[LatteMaid],
        sub: app_commands.Range[str, 1, 20] | None = None,
        args: str | None = None,
    ) -> None:
        """Jishaku

        Attributes:
            sub (str): The subcommand to use.
            args (str): The arguments to pass to the subcommand.
        """

        await interaction.response.defer(ephemeral=True)

        jsk = self.bot.get_command('jishaku' if sub is None else f'jishaku {sub}')

        if jsk is None:
            raise UserInputError(f"Couldn't find command `jishaku {sub}`.")

        ctx = await self.bot.get_context(interaction)
        ctx.invoked_with = jsk.qualified_name
        ctx.command = jsk
        if args:
            ctx.view = StringView(args)
        await self.bot.invoke(ctx)

    @jishaku_app.autocomplete('sub')
    async def jishaku_app_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        subs: list[str] = []

        for command in self.walk_commands():
            if command == self.jsk:
                continue

            subs.append(command.qualified_name)
            subs.extend(command.aliases)

        # remove parent command name
        subs = [sub.removeprefix('jishaku ') for sub in sorted(subs)]

        if not current:
            return [app_commands.Choice(name=sub, value=sub.lower()) for sub in subs][:25]

        return [app_commands.Choice(name=sub, value=sub.lower()) for sub in subs if current.lower() in sub.lower()][:25]

    @app_commands.default_permissions(administrator=True)
    @bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    @owner_only()
    async def ctx_message_jishaku_python(
        self,
        interaction: discord.Interaction[LatteMaid],
        message: discord.Message,
    ) -> None:
        if not message.content:
            raise UserInputError('No code provided.')

        await interaction.response.defer(ephemeral=message.content.startswith('_'))

        content = message.content.removeprefix('_').strip()

        jsk = self.bot.get_command('jishaku py')
        ctx = await self.bot.get_context(interaction)
        codeblock = codeblock_converter(content)

        try:
            await jsk(ctx, argument=codeblock)  # type: ignore
        except Exception as e:
            _log.error(e)
            raise UserInputError('Invalid Python code.') from e


async def setup(bot: LatteMaid) -> None:
    if bot.support_guild_id is not None:
        await bot.add_cog(Jishaku(bot=bot), guilds=[discord.Object(id=bot.support_guild_id)])
    else:
        _log.warning('support guild id is not set. Jishaku cog will not be loaded.')
