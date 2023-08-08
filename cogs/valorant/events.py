import logging

from discord.ext import commands

from core.i18n import I18n

from .abc import MixinMeta
from .auth import RiotAuth

_log = logging.getLogger(__name__)


_ = I18n('valorant.events', __file__, read_only=True)


class Events(MixinMeta):
    @commands.Cog.listener()
    async def on_re_authorized_successfully(self, riot_auth: RiotAuth) -> None:
        if riot_auth.owner_id is None:
            _log.debug(f'riot_auth owner_id is None, not updating database')
            return

        assert riot_auth.user_id is not None

        await self.bot.db.update_riot_account(
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
        )
        # # invalidate cache
        # try:
        #     self.fetch_user.invalidate(self, id=riot_auth.discord_id)  # type:
        # except Exception:
        #     pass

    @commands.Cog.listener()
    async def on_re_authorize_failed(self, riot_auth: RiotAuth) -> None:
        """Called when a user's riot account fails to update"""
        _log.info(f'riot_auth failed to re-authorized {riot_auth.puuid} for {riot_auth.owner_id}')
        # self.cache_invalidate(riot_auth)  # validate cache

    # @commands.Cog.listener()
    # async def on_re_authorize_forbidden(self, user_agent: str) -> None:
    #     """Called when a user's riot account fails to update"""
    #     _log.info(f'User agent {user_agent} is forbidden')

    # @commands.Cog.listener()
    # async def on_valorant_version_update(self) -> None:
    #     ...
