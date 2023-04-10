import asyncio
import contextlib
import logging
from logging.handlers import RotatingFileHandler

import config
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from core.bot import LatteMaid

try:
    import uvloop  # type: ignore
except ImportError:
    pass
else:
    uvloop.install()


class RemoveNoise(logging.Filter):
    def __init__(self):
        super().__init__(name='discord.state')

    def filter(self, record):
        if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
            return False
        return True


@contextlib.contextmanager
def setup_logging():
    log = logging.getLogger()

    try:
        # __enter__
        max_bytes = 32 * 1024 * 1024  # 32 MiB
        # discord.py
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.state').addFilter(RemoveNoise())
        # valorantx
        logging.getLogger('valorantx').setLevel(logging.INFO)
        logging.getLogger('valorantx.http').setLevel(logging.WARNING)

        log.setLevel(logging.INFO)
        handler = RotatingFileHandler(
            filename='_lattemaid.log', encoding='utf-8', mode='w', maxBytes=max_bytes, backupCount=5
        )
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for handler in handlers:
            handler.close()
            log.removeHandler(handler)


def main():
    with setup_logging():
        asyncio.run(run_bot())


def create_engine() -> AsyncEngine:
    # uri = config.postgresql
    uri = config.sqlite_test
    return create_async_engine(uri, echo=True)


async def run_bot():
    log = logging.getLogger()
    engine = create_engine()
    try:
        engine = create_engine()
    except Exception as e:
        log.exception('Failed to create database pool', exc_info=e)
        return

    async with LatteMaid() as bot:
        bot.db_engine = engine
        bot.db_session = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        bot._debug = config.debug
        await bot.start()

    # TODO: webhook notify on bot start/stop


if __name__ == '__main__':
    if config.debug:
        logging.basicConfig(level=logging.DEBUG, format=f'%(asctime)s:%(levelname)s:%(name)s: %(message)s')
    main()
