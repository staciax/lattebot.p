from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

# i18n
from discord.app_commands import locale_str as _T

import valorantx2 as valorantx
from core.checks import cooldown_medium, dynamic_cooldown
from core.cog import context_menu
from core.errors import BadArgument
from core.i18n import I18n
from valorantx2.utils import validate_riot_id

from .abc import MixinMeta
from .account_manager import AccountManager

if TYPE_CHECKING:
    from core.bot import LatteMiad

SUPPORT_GUILD_ID = 1097859504906965042

_log = logging.getLogger(__name__)

_ = I18n('valorant.context_menu', __file__, read_only=True)


class ContextMenu(MixinMeta):
    @context_menu(name=_T('party invite'), guilds=[discord.Object(id=SUPPORT_GUILD_ID)])
    @dynamic_cooldown(cooldown_medium)
    async def message_invite_to_party(
        self,
        interaction: discord.Interaction[LatteMiad],
        message: discord.Message,
    ) -> None:
        """Invite the author of the message to the party."""

        try:
            game_name, tag_line = validate_riot_id(message.content)
        except ValueError:
            raise BadArgument(_('invalid.riot_id', interaction.locale))

        await interaction.response.defer(ephemeral=True)

        user = await self.get_user(interaction.user.id)  # type: ignore
        account_manager = AccountManager(user, self.bot)
        await account_manager.wait_until_ready()

        try:
            party_player = await self.valorant_client.fetch_party_player(riot_auth=account_manager.main_account)
        except valorantx.errors.NotFound:
            raise BadArgument(_('not_in_party', interaction.locale))
        else:
            if account_manager.main_account is None:
                raise BadArgument(_('not_logged_in', interaction.locale))
            party = await self.valorant_client.party_invite_by_riot_id(
                party_player.current_party_id,
                game_name,
                tag_line,
                riot_auth=account_manager.main_account,
            )
            if party.version == 0:
                raise BadArgument(_('not_in_party', interaction.locale))
            await interaction.followup.send('Invited.', ephemeral=True, silent=True)

    @context_menu(name=_T('party request'), guilds=[discord.Object(id=SUPPORT_GUILD_ID)])
    @dynamic_cooldown(cooldown_medium)
    async def user_request_to_party(
        self, interaction: discord.Interaction[LatteMiad], user: discord.User | discord.Member
    ) -> None:
        # author
        author = await self.get_user(interaction.user.id)  # type: ignore
        author_account_manager = AccountManager(author, self.bot)
        await author_account_manager.wait_until_ready()

        author_main_account = author_account_manager.main_account
        if author_main_account is None:
            raise BadArgument('You are not logged in.')

        if author_main_account.game_name is None or author_main_account.tag_line is None:
            raise RuntimeError('game_name or tag_line is None')

        # target
        target = await self.get_user(user.id)  # type: ignore
        target_account_manager = AccountManager(target, self.bot)
        await target_account_manager.wait_until_ready()

        # party
        target_riot_auth = target_account_manager.main_account
        target_party_pleyer = await self.valorant_client.fetch_party_player(riot_auth=target_riot_auth)
        await self.valorant_client.http.post_party_invite_by_display_name(
            party_id=target_party_pleyer.current_party_id,
            name=author_main_account.game_name,
            tag=author_main_account.tag_line,
        )

        await interaction.response.send_message('Not implemented.', ephemeral=True, silent=True)

    # avaliable in 1.0.0a

    @context_menu(name=_T('match history'))
    @dynamic_cooldown(cooldown_medium)
    async def message_match_history(self, interaction: discord.Interaction[LatteMiad], message: discord.Message) -> None:
        try:
            game_name, tag_line = validate_riot_id(message.content)
        except ValueError:
            raise BadArgument(_('invalid.riot_id', interaction.locale))

        await interaction.response.defer(ephemeral=True)

        # riot user
        riot_user = await self.valorant_client.fetch_partial_user(game_name, tag_line)

        # match history
        match_history = await self.valorant_client.fetch_match_history(puuid=riot_user.puuid, end=6)
