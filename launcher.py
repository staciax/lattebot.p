import argparse
import asyncio
import contextlib
import logging
import os
from logging.handlers import RotatingFileHandler

from discord import SyncWebhook, utils

from core.bot import LatteMaid

try:
    import uvloop  # type: ignore
except ImportError:
    pass
else:
    uvloop.install()

parser = argparse.ArgumentParser()
parser.add_argument(
    '-p',
    '--prod',
    action='store_true',
    help='run in production mode.',
)
parser.add_argument(
    '-s',
    '--sync',
    # choices=('all', 'guild'),
    action='store_true',
    help='sync application commands to discord.',
)
args = parser.parse_args()


# inspired by robodanny - Danny (Rapptz)


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
        logging.getLogger('valorantx.valorant_api').setLevel(logging.INFO)
        logging.getLogger('valorantx.valorant_api.http').setLevel(logging.WARNING)

        log.setLevel(logging.INFO if args.prod else logging.DEBUG)
        handler = RotatingFileHandler(
            filename='_lattemaid.log', encoding='utf-8', mode='w', maxBytes=max_bytes, backupCount=5
        )
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)
        if not args.prod:
            handler = logging.StreamHandler()
            if isinstance(handler, logging.StreamHandler) and utils.stream_supports_colour(handler.stream):
                fmt = utils._ColourFormatter()
            handler.setFormatter(fmt)
            log.addHandler(handler)
        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for handler in handlers:
            handler.close()
            log.removeHandler(handler)


@contextlib.contextmanager
def setup_webhook():
    # inspired by ayane-bot - Buco7854(github)
    if args.prod:
        yield
    url = os.getenv('WEBHOOK_STATUS_URI')
    # token = os.getenv('DISCORD_TOKEN')
    assert url is not None, 'Webhook URI is not set'
    try:
        webhook = SyncWebhook.from_url(url)
        webhook.send('☕ LatteMaid is drinking coffee!')
        yield
    finally:
        webhook.send('💤 LatteMaid is going to sleep!')


def main():
    with setup_logging(), setup_webhook():
        asyncio.run(run_bot())


async def run_bot():
    async with LatteMaid(
        debug_mode=args.prod,
        tree_sync_at_startup=args.sync,
    ) as bot:
        await bot.start()


if __name__ == '__main__':
    main()
