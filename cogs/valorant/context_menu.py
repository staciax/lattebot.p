from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union

import discord

# i18n
from discord.app_commands import locale_str as _T

import valorantx2 as valorantx
from core.checks import cooldown_medium, dynamic_cooldown
from core.cog import context_menu
from core.errors import BadArgument
from core.i18n import I18n

from .abc import MixinMeta
from .account_manager import AccountManager

if TYPE_CHECKING:
    from core.bot import LatteMaid


_log = logging.getLogger(__name__)


_ = I18n('valorant.context_menu', __file__, read_only=True)

SUPPORT_GUILD_ID = 1097859504906965042


class ContextMenu(MixinMeta):
    @context_menu(name=_T('party invite'), guilds=[discord.Object(id=SUPPORT_GUILD_ID)])
    @dynamic_cooldown(cooldown_medium)
    async def message_invite_to_party(
        self,
        interaction: discord.Interaction[LatteMaid],
        message: discord.Message,
    ) -> None:
        """Invite the author of the message to the party."""

        if '#' not in message.content:
            raise BadArgument('Invalid Riot ID.')

        await interaction.response.defer(ephemeral=True)

        user = await self.get_user(interaction.user.id)  # type: ignore
        account_manager = AccountManager(user, self.bot)
        await account_manager.wait_until_ready()

        game_name, _, tag_line = message.content.partition('#')

        if not game_name or not tag_line:
            raise BadArgument('Invalid Riot ID.')

        if len(game_name) > 16:
            raise BadArgument('Invalid Riot ID.')

        if len(tag_line) > 5:
            raise BadArgument('Invalid Riot ID.')

        try:
            party_player = await self.valorant_client.fetch_party_player(riot_auth=account_manager.first_account)
        except valorantx.errors.NotFound:
            await interaction.followup.send('You are not in a party.', ephemeral=True, silent=True)
            return
        else:
            party = await self.valorant_client.party_invite_by_riot_id(
                party_player.current_party_id,
                game_name,
                tag_line,
                riot_auth=account_manager.first_account,
            )
            if party.version == 0:
                raise BadArgument(f'Not found: {game_name}#{tag_line}')
            await interaction.followup.send('Invited.', ephemeral=True, silent=True)

    @context_menu(name=_T('party request'), guilds=[discord.Object(id=SUPPORT_GUILD_ID)])
    @dynamic_cooldown(cooldown_medium)
    async def user_request_to_party(
        self, interaction: discord.Interaction[LatteMaid], user: Union[discord.User, discord.Member]
    ) -> None:
        # target
        target = await self.get_user(user.id)  # type: ignore
        target_account_manager = AccountManager(target, self.bot)
        await target_account_manager.wait_until_ready()

        # author
        author = await self.get_user(interaction.user.id)  # type: ignore
        author_account_manager = AccountManager(author, self.bot)
        await author_account_manager.wait_until_ready()

        await interaction.response.send_message('Not implemented.', ephemeral=True, silent=True)
