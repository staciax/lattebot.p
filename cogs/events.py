from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union

import discord
from discord.app_commands import Command, ContextMenu
from discord.ext import commands

from core.embed import Embed

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__name__)


class Event(commands.Cog, name='events'):
    """Bot Events"""

    def __init__(self, bot: LatteMaid) -> None:
        self.bot: LatteMaid = bot

    @discord.utils.cached_property
    def webhook(self) -> discord.Webhook:
        wh_id, wh_token = self.bot.config.stat_webhook
        hook = discord.Webhook.partial(id=wh_id, token=wh_token, session=self.bot.session)
        return hook

    @commands.Cog.listener('on_app_command_completion')
    async def on_latte_app_command(
        self, interaction: discord.Interaction[LatteMaid], command: Union[Command, ContextMenu]
    ) -> None:
        ...
        # await interaction.client.pool.execute(
        #     "INSERT INTO commands (guild_id, user_id, command, timestamp) VALUES ($1, $2, $3, $4)",
        #     getattr(interaction.guild, "id", None),
        #     interaction.user.id,
        #     command.qualified_name,
        #     interaction.created_at,
        # )

    #     """Called when a command is completed"""

    #     if interaction.user == self.bot.owner:
    #         return

    # data = self.bot.app_stats.get(command.name)
    # if data is not None:
    #     await self.bot.app_stats.put(command.name, data + 1)
    # else:
    #     await self.bot.app_stats.put(command.name, 1)

    # @commands.Cog.listener('on_message_edit')
    # async def on_latte_message_edit(self, before: discord.Message, after: discord.Message) -> None:
    #     if before.author.bot:
    #         return

    #     if before.content == after.content:
    #         return

    #     await self.bot.process_commands(after)

    async def send_guild_stats(self, embed: discord.Embed, guild: discord.Guild):
        """Send guild stats to webhook"""

        member_count = guild.member_count or 1

        embed.description = (
            f'**ɴᴀᴍᴇ:** {discord.utils.escape_markdown(guild.name)} • `{guild.id}`\n' f'**ᴏᴡɴᴇʀ:** `{guild.owner_id}`'
        )
        embed.add_field(name='ᴍᴇᴍʙᴇʀ ᴄᴏᴜɴᴛ', value=f'{member_count}', inline=True)
        embed.set_thumbnail(url=guild.icon)
        embed.set_footer(text=f'ᴛᴏᴛᴀʟ ɢᴜɪʟᴅꜱ: {len(self.bot.guilds)}')

        if guild.me:
            embed.timestamp = guild.me.joined_at

        await self.webhook.send(embed=embed, silent=True)

    @commands.Cog.listener('on_guild_join')
    async def on_latte_join(self, guild: discord.Guild) -> None:
        """Called when LatteMaid joins a guild"""

        if guild.id in self.bot.db.blacklist:
            _log.info(f'left guild {guild.id} because it is blacklisted')
            return await guild.leave()

        embed = Embed(title='ᴊᴏɪɴᴇᴅ ꜱᴇʀᴠᴇʀ').success()
        await self.send_guild_stats(embed, guild)

    @commands.Cog.listener('on_guild_remove')
    async def on_latte_leave(self, guild: discord.Guild) -> None:
        """Called when LatteMaid leaves a guild"""
        embed = Embed(title='ʟᴇꜰᴛ ꜱᴇʀᴠᴇʀ').error()
        await self.send_guild_stats(embed, guild)


async def setup(bot: LatteMaid) -> None:
    await bot.add_cog(Event(bot))
