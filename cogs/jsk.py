from __future__ import annotations

import inspect
import io
import logging
import pathlib
from typing import TYPE_CHECKING, Any, Callable

import discord
from discord import app_commands
from discord.app_commands import locale_str as _T

# from discord.app_commands.checks import bot_has_permissions
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check
from jishaku.repl import AsyncCodeExecutor, get_var_dict_from_ctx  # type: ignore

from core.checks import owner_only
from core.errors import LatteMaidError

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__file__)

# https://github.com/Gorialis/jishaku


class Jishaku(*OPTIONAL_FEATURES, *STANDARD_FEATURES, name='jishaku'):
    if TYPE_CHECKING:
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

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.ctx_msg_jsk_py)
        await super().cog_load()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_msg_jsk_py.name, type=self.ctx_msg_jsk_py.type)
        await super().cog_unload()

    @Feature.Command(name="jishaku", aliases=["jsk"], invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: commands.Context) -> None:
        """
        The Jishaku debug and diagnostic commands.

        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """
        embed = discord.Embed(title="Jishaku", color=discord.Color.blurple())
        await ctx.send(embed=embed, silent=True)

    @Feature.Command(parent="jsk", name="source", aliases=["src"])
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
            await ctx.send(f"Was unable to retrieve the source for `{command}` for some reason.")
            return

        filename = "source.py"

        try:
            filename = pathlib.Path(inspect.getfile(command.callback)).name  # type: ignore
        except (TypeError, OSError):
            pass

        # getsourcelines for some reason returns WITH line endings
        source_text = ''.join(source_lines)

        if use_file_check(ctx, len(source_text)):  # File "full content" preview limit
            await ctx.send(file=discord.File(filename=filename, fp=io.BytesIO(source_text.encode('utf-8'))))
        else:
            paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1980)

            paginator.add_line(source_text.replace('```', '``\N{zero width space}`'))

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            await interface.send_to(ctx)

    @Feature.Command(parent="jsk", name="py", aliases=["python"])
    async def jsk_python(self, ctx: ContextA, *, argument: codeblock_converter):  # type: ignore
        if TYPE_CHECKING:
            argument: Codeblock = argument  # type: ignore

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

    @owner_only()
    @app_commands.default_permissions(administrator=True)
    # @bot_has_permissions(administrator=True)
    async def ctx_message_jishaku_python(
        self, interaction: discord.Interaction[LatteMaid], message: discord.Message
    ) -> None:
        if not message.content:
            raise LatteMaidError('No code provided.')

        await interaction.response.defer(ephemeral=message.content.startswith('_'))

        content = message.content.removeprefix('_').strip()

        jsk = self.bot.get_command(f'jishaku py')
        ctx = await commands.Context.from_interaction(interaction)
        codeblock = codeblock_converter(content)

        try:
            await jsk(ctx, argument=codeblock)  # type: ignore
        except Exception as e:
            _log.error(e)
            raise LatteMaidError('Invalid Python code.') from e


async def setup(bot: LatteMaid) -> None:
    if bot.support_guild_id is not None:
        await bot.add_cog(Jishaku(bot=bot), guilds=[discord.Object(id=bot.support_guild_id)])
    else:
        _log.warning('support guild id is not set. Jishaku cog will not be loaded.')
