import datetime as dt
import logging

from discord.ext import tasks

from core.i18n import I18n

from .abc import MixinMeta
from .auth import RiotAuth

_log = logging.getLogger(__name__)

_ = I18n('valorant.schedule', __file__, read_only=True)

utc7 = dt.timezone(dt.timedelta(hours=7))
times = [
    dt.time(hour=6, minute=30, tzinfo=utc7),  # 6:30 AM UTC+7
    dt.time(hour=20, tzinfo=utc7),  # 8:00 PM UTC+7
]


class Schedule(MixinMeta):
    async def do_checker_version(self) -> None:
        _log.info(f'checking valorant version')
        version = await self.valorant_client.valorant_api.fetch_version()

        if version != self.valorant_client.version:
            self.valorant_client.version = version
            await self.valorant_client.valorant_api.reload()
            RiotAuth.RIOT_CLIENT_USER_AGENT = (
                f'RiotClient/{version.riot_client_build} %s (Windows;10;;Professional, x64)'
            )
            _log.info(f'valorant client version updated to {version}')

    @tasks.loop(time=times)
    async def version_checker(self) -> None:
        await self.do_checker_version()

    @version_checker.before_loop
    async def before_version_checker(self) -> None:
        await self.bot.wait_until_ready()
        if not self.valorant_client.is_ready():
            return
        _log.info(f'valorant version checker loop has been started')

    @version_checker.after_loop
    async def after_version_checker(self) -> None:
        if self.version_checker.is_being_cancelled():
            _log.info(f'valorant version checker loop has been cancelled')
        else:
            _log.info(f'valorant version checker loop has been stopped')

    # cache control
    # every 6:30 AM UTC+7

    def do_cache_clear(self) -> None:
        for method in self.valorant_client.__dict__.values():
            if hasattr(method, 'cache_clear'):
                method.cache_clear()
        _log.info(f'valorant client cache cleared')

    @tasks.loop(time=dt.time(hour=6, minute=30, tzinfo=utc7))
    async def cache_control(self) -> None:
        self.do_cache_clear()

    @cache_control.before_loop
    async def before_cache_control(self) -> None:
        await self.bot.wait_until_ready()
        if not self.valorant_client.is_ready():
            return
        _log.info(f'valorant cache control loop has been started')

    @cache_control.after_loop
    async def after_cache_control(self) -> None:
        if self.cache_control.is_being_cancelled():
            self.do_cache_clear()
            _log.info('valorant cache control loop has been cancelled')
        else:
            _log.info('valorant cache control loop has been stopped')
