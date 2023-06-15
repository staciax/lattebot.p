from __future__ import annotations

import datetime
import itertools
import platform

# from functools import lru_cache
from typing import TYPE_CHECKING, Optional, Type

import discord
import psutil
import pygit2

# import pkg_resources
from discord import Interaction, app_commands, ui
from discord.app_commands import locale_str as _T
from discord.app_commands.checks import bot_has_permissions, dynamic_cooldown
from discord.ext import commands
from discord.utils import format_dt

from core.checks import cooldown_short
from core.ui.embed import MiadEmbed
from core.utils.useful import count_python

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from core.utils.enums import Emoji


class About(commands.Cog, name='about'):

    """Latte's About command"""

    def __init__(self, bot: LatteMaid) -> None:
        self.bot: LatteMaid = bot
        self.emoji: Type[Emoji] = bot.emoji
        self.process = psutil.Process()

    @property
    def display_emoji(self) -> Optional[discord.Emoji]:
        return self.bot.get_emoji(998453861511610398)

    @staticmethod
    def format_commit(commit: pygit2.Commit) -> str:
        """format a commit"""
        short, _, _ = commit.message.partition('\n')
        short = short[0:40] + '...' if len(short) > 40 else short
        short_sha2 = commit.hex[0:6]
        commit_tz = datetime.timezone(datetime.timedelta(minutes=commit.commit_time_offset))
        commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)
        offset = format_dt(commit_time, style='R')
        return f'[`{short_sha2}`](https://github.com/staciax/latte-maid/commit/{commit.hex}) {short} ({offset})'

    @staticmethod
    def get_last_parent() -> str:
        """Get the last parent of the repo"""
        repo = pygit2.Repository('./.git')
        parent = repo.head.target.hex  # type: ignore
        return parent[0:6]

    # @lru_cache(maxsize=1)
    def get_latest_commits(self, limit: int = 3) -> str:
        """Get the latest commits from the repo"""
        repo = pygit2.Repository('./.git')
        commits = list(itertools.islice(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), limit))
        return '\n'.join(self.format_commit(c) for c in commits)

    @app_commands.command(name=_T('invite'), description=_T('Invite bot'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @dynamic_cooldown(cooldown_short)
    async def invite(self, interaction: Interaction[LatteMaid]) -> None:
        embed = MiadEmbed().secondary()
        embed.set_author(
            name=f'{self.bot.user.name} ɪɴᴠɪᴛᴇ',  # type: ignore
            url=self.bot.invite_url,
            icon_url=self.bot.user.avatar,  # type: ignore
        )
        embed.set_footer(text=f'{self.bot.user.name} | v{self.bot.version}')  # type: ignore
        # embed.set_image(url=str(self.cdn.invite_banner))

        view = ui.View()
        view.add_item(ui.Button(label='ɪɴᴠɪᴛᴇ ᴍᴇ', url=self.bot.invite_url, emoji=str(self.emoji.latte_icon)))

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name=_T('about'), description=_T('Shows bot information'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @dynamic_cooldown(cooldown_short)
    async def about(self, interaction: Interaction[LatteMaid]) -> None:
        # await interaction.response.defer()

        e = self.bot.emoji

        core_dev = self.bot.owner
        guild_count = len(self.bot.guilds)
        channel_count = len(list(self.bot.get_all_channels()))
        member_count = sum(guild.member_count for guild in self.bot.guilds if guild.member_count is not None)
        total_commands = len(self.bot.tree.get_commands())
        # dpy_version = pkg_resources.get_distribution("discord.py").version
        memory_usage = self.process.memory_full_info().uss / 1024**2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()

        embed = MiadEmbed(timestamp=interaction.created_at).purple()
        embed.set_author(name='About Me', icon_url=self.bot.user.avatar)  # type: ignore
        embed.add_field(name='ʟᴀᴛᴇꜱᴛ ᴜᴘᴅᴀᴛᴇꜱ:', value=self.get_latest_commits(limit=5), inline=False)
        embed.add_field(
            name='ꜱᴛᴀᴛꜱ:',
            value=f'{e.latte_icon} ꜱᴇʀᴠᴇʀꜱ: `{guild_count}`\n'
            + f'{e.member_icon} ᴜꜱᴇʀꜱ: `{member_count}`\n'
            + f'{e.slash_command} ᴄᴏᴍᴍᴀɴᴅꜱ: `{total_commands}`\n'
            + f'{e.channel_icon} ᴄʜᴀɴɴᴇʟ: `{channel_count}`',
            inline=True,
        )
        embed.add_field(
            name='ʙᴏᴛ ɪɴꜰᴏ:',
            value=f'{e.cursor} ʟɪɴᴇ ᴄᴏᴜɴᴛ: `{count_python(".")}`\n'
            + f'{e.latte_icon} ʟᴀᴛᴛᴇ_ᴍᴀɪᴅ: `{self.bot._version}`\n'
            + f'{e.python} ᴘʏᴛʜᴏɴ: `{platform.python_version()}`\n'
            + f'{e.discord_py} ᴅɪꜱᴄᴏʀᴅ.ᴘʏ: `{discord.__version__}`',  # dpy_version[:dpy_version.find('+')]
            inline=True,
        )
        embed.add_field(name='\u200b', value='\u200b', inline=True)
        embed.add_field(
            name='ᴘʀᴏᴄᴇꜱꜱ:',
            value=f'ᴏꜱ: `{platform.system()}`\n'
            + f'ᴄᴘᴜ ᴜꜱᴀɢᴇ: `{cpu_usage}%`\n'
            + f'ᴍᴇᴍᴏʀʏ ᴜꜱᴀɢᴇ: `{round(memory_usage, 2)} MB`',
            inline=True,
        )
        embed.add_field(
            name='ᴜᴘᴛɪᴍᴇ:',
            value=f'ʙᴏᴛ: <t:{round(self.bot.launch_time.timestamp())}:R>\n'
            + f'ꜱʏꜱᴛᴇᴍ: <t:{round(psutil.boot_time())}:R>',
            inline=True,
        )
        embed.add_field(name='\u200b', value='\u200b', inline=True)
        embed.set_footer(text=f'ᴅᴇᴠᴇʟᴏᴘᴇᴅ ʙʏ {core_dev}', icon_url=core_dev.avatar)

        view = ui.View()
        view.add_item(
            ui.Button(label='ꜱᴜᴘᴘᴏʀᴛ ꜱᴇʀᴠᴇʀ', url=self.bot.support_invite_url, emoji=str(self.emoji.latte_icon))
        )
        view.add_item(
            ui.Button(
                label='ᴅᴇᴠᴇʟᴏᴘᴇʀ',
                url=f'https://discord.com/users/{core_dev.id}',
                emoji=str(self.emoji.stacia_dev),
            )
        )

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name=_T('support'), description=_T('Sends the support server of the bot.'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @dynamic_cooldown(cooldown_short)
    async def support(self, interaction: Interaction[LatteMaid]) -> None:
        embed = MiadEmbed()
        embed.set_author(name='ꜱᴜᴘᴘᴏʀᴛ:', icon_url=self.bot.user.avatar, url=self.bot.support_invite_url)  # type: ignore
        embed.set_thumbnail(url=self.bot.user.avatar)  # type: ignore

        view = ui.View()
        view.add_item(
            ui.Button(label='ꜱᴜᴘᴘᴏʀᴛ ꜱᴇʀᴠᴇʀ', url=self.bot.support_invite_url, emoji=str(self.emoji.latte_icon))
        )
        view.add_item(
            ui.Button(
                label='ᴅᴇᴠᴇʟᴏᴘᴇʀ',
                url=f'https://discord.com/users/{self.bot.owner_id}',
                emoji=str(self.emoji.stacia_dev),
            )
        )

        await interaction.response.send_message(embed=embed, view=view)

    # @app_commands.command(name=_T("i18n"), description=_T("Shows the current language of the bot."))
    # @app_commands.guild_only()
    # @dynamic_cooldown(cooldown_5s)
    # async def i18n(self, interaction: Interaction) -> None:
    #     await interaction.response.send_message('')

    # @app_commands.command(name=_T('source'), description=_T('Shows the source code of the bot.'))
    # @app_commands.describe(command=_T('The command to show the source code of.'))
    # @dynamic_cooldown(cooldown_5s)
    # @app_commands.guild_only()
    # async def source(self, interaction: Interaction, command: str) -> None:
    #     ...

    # @source.autocomplete('command')
    # async def source_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:

    #     entries = []

    #     namespace = interaction.namespace.command

    #     for command in self.bot.get_app_commands():
    #         if not namespace:
    #             entries.append(command)
    #         else:
    #             if command.qualified_name.startswith(namespace):
    #                 entries.append(command)

    #     return [app_commands.Choice(name=entry.qualified_name, value=entry.id) for entry in entries][:25]
