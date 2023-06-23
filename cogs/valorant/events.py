import datetime
import logging

# from discord import app_commands
# from discord.app_commands import locale_str as _T
from discord.ext import commands, tasks

from core.i18n import I18n

from .abc import MixinMeta
from .auth import RiotAuth

_log = logging.getLogger(__name__)

utc7 = datetime.timezone(datetime.timedelta(hours=7))
times = [
    datetime.time(hour=6, minute=30, tzinfo=utc7),  # 6:30 AM UTC+7
    datetime.time(hour=20, tzinfo=utc7),  # 8:00 PM UTC+7
]

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

    @commands.Cog.listener()
    async def on_valorant_version_update(self) -> None:
        ...

    async def do_checker_valorant_version(self) -> None:
        _log.info(f'checking valorant version')
        version = await self.valorant_client.valorant_api.fetch_version()

        if version is None:
            _log.warning(f'failed to fetch valorant version')
            return

        if version != self.valorant_client.version:
            self.valorant_client.version = version
            # TODO: make method to update version
            await self.valorant_client.valorant_api.cache.init()
            RiotAuth.RIOT_CLIENT_USER_AGENT = (
                f'RiotClient/{version.riot_client_build} %s (Windows;10;;Professional, x64)'
            )
            _log.info(f'valorant client version updated to {version}')

    @tasks.loop(time=times)
    async def valorant_version_checker(self) -> None:
        await self.do_checker_valorant_version()

    @valorant_version_checker.before_loop
    async def before_valorant_version_checker(self) -> None:
        await self.bot.wait_until_ready()
        if not self.valorant_client.is_ready():
            return
        _log.info(f'valorant version checker loop has been started')

    @valorant_version_checker.after_loop
    async def after_valorant_version_checker(self) -> None:
        if self.valorant_version_checker.is_being_cancelled():
            _log.info(f'valorant version checker loop has been cancelled')
        else:
            _log.info(f'valorant version checker loop has been stopped')

    # cache control
    # every 6:30 AM UTC+7

    def do_cache_control(self) -> None:
        for method in self.valorant_client.__dict__.values():
            if hasattr(method, 'cache_clear'):
                method.cache_clear()
        _log.info(f'valorant client cache cleared')

    @tasks.loop(time=datetime.time(hour=6, minute=30, tzinfo=utc7))
    async def valorant_cache_control(self) -> None:
        self.do_cache_control()

    @valorant_cache_control.before_loop
    async def before_valorant_cache_control(self) -> None:
        await self.bot.wait_until_ready()
        if not self.valorant_client.is_ready():
            return
        _log.info(f'valorant cache control loop has been started')

    @valorant_cache_control.after_loop
    async def after_valorant_cache_control(self) -> None:
        if self.valorant_cache_control.is_being_cancelled():
            self.do_cache_control()
            _log.info(f'valorant cache control loop has been cancelled')
        else:
            _log.info(f'valorant cache control loop has been stopped')
