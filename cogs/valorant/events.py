from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

# from discord import app_commands
# from discord.app_commands import locale_str as _T
from discord.ext import commands, tasks

from .abc import MixinMeta
from .valorantx2.auth import RiotAuth

if TYPE_CHECKING:
    from .valorantx2.auth import RiotAuth

_log = logging.getLogger(__name__)


class Events(MixinMeta):
    @commands.Cog.listener()
    async def on_re_authorized_success(self, riot_auth: RiotAuth, wait_for: bool) -> None:
        if wait_for:
            if riot_auth.owner_id is None:
                _log.debug(f'riot_auth owner_id is None, not updating database')
                return

            assert riot_auth.user_id is not None

            if await self.bot.db.update_riot_account(
                puuid=riot_auth.user_id,
                owner_id=riot_auth.owner_id,
                game_name=riot_auth.game_name,
                tag_line=riot_auth.tag_line,
                region=riot_auth.region,
                scope=riot_auth.scope,
                token_type=riot_auth.token_type,
                expires_at=riot_auth.expires_at,
                id_token=riot_auth.id_token,
                access_token=riot_auth.access_token,
                entitlements_token=riot_auth.entitlements_token,
                ssid=riot_auth.get_ssid(),
            ):
                _log.info(f"riot_auth {riot_auth.puuid} successfully updated in database for {riot_auth.owner_id}")
            else:
                _log.info(f"riot_auth {riot_auth.puuid} failed to update in database for {riot_auth.owner_id}")

            # # invalidate cache
            # try:
            #     self.fetch_user.invalidate(self, id=riot_auth.discord_id)  # type:
            # except Exception:
            #     pass

    @commands.Cog.listener()
    async def on_re_authorize_fail(self, riot_auth: RiotAuth) -> None:
        """Called when a user's riot account fails to update"""
        _log.info(f'riot_auth failed to re-authorized {riot_auth.puuid} for {riot_auth.owner_id}')
        # self.cache_invalidate(riot_auth)  # validate cache

    # @commands.Cog.listener()
    # async def on_re_authorize_forbidden(self, user_agent: str) -> None:
    #     """Called when a user's riot account fails to update"""
    #     _log.info(f'User agent {user_agent} is forbidden')

    @commands.Cog.listener()
    async def on_valorant_version_update(self) -> None:
        ...

    @tasks.loop(time=datetime.time(hour=17, minute=0, second=0))  # looping every 00:00:00 UTC+7
    async def valorant_client_version(self) -> None:
        version = await self.valorant_client.valorant_api.fetch_version()

        if version is None:
            return

        if version != self.valorant_client.version:
            self.valorant_client._version = version
            # TODO: make method to update version
            await self.valorant_client.valorant_api.init()
            RiotAuth.RIOT_CLIENT_USER_AGENT = (
                f'RiotClient/{version.riot_client_build} %s (Windows;10;;Professional, x64)'
            )
            _log.info(f'valorant client version updated to {version}')

    @valorant_client_version.before_loop
    async def before_valorant_client_version(self) -> None:
        await self.bot.wait_until_ready()
        await self.valorant_client.wait_until_ready()
