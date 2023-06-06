from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from discord import app_commands
from discord.app_commands import locale_str as _T
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
            user = await self.bot.db.get_user(riot_auth.discord_id)

            if user is None:
                return

            riot_auth_db = user.get_riot_account(riot_auth.puuid)
            # await riot_auth.reauthorize(wait_for=False)

            # v_user = await self.fetch_user(id=riot_auth.discord_id)
            # for acc in v_user.get_riot_accounts():
            #     if acc.puuid != riot_auth.puuid:
            #         await acc.re_authorize(wait_for=False)

            # # wait for re_authorize
            # async with self.bot.pool.acquire() as conn:
            #     # Update the riot account in the database

            #     old_data = self._get_user(riot_auth.discord_id)
            #     if old_data is not None:
            #         new_data = [
            #             riot_auth if auth_u.puuid == riot_auth.puuid else auth_u
            #             for auth_u in old_data.get_riot_accounts()
            #         ]

            #         payload = [user_riot_auth.to_dict() for user_riot_auth in new_data]

            #         dumps_payload = json.dumps(payload)

            #         # encryption
            #         encrypt_payload = self.bot.encryption.encrypt(dumps_payload)

            #         await self.db.upsert_user(
            #             encrypt_payload,
            #             v_user.id,
            #             v_user.guild_id,
            #             v_user.locale,
            #             v_user.date_signed,
            #             conn=conn,
            #         )

            # # invalidate cache
            # try:
            #     self.fetch_user.invalidate(self, id=riot_auth.discord_id)  # type:
            # except Exception:
            #     pass
        # _log.info(f'User {riot_auth.discord_id} re-authorized')

    @commands.Cog.listener()
    async def on_re_authorize_fail(self, riot_auth: RiotAuth) -> None:
        """Called when a user's riot account fails to update"""
        # self.cache_invalidate(riot_auth)  # validate cache
        # _log.info(f'User {riot_auth.discord_id} failed to re-authorized')

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
