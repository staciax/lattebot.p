from __future__ import annotations

import asyncio
import datetime
import logging
import os
import random
from typing import TYPE_CHECKING, Any, Literal, overload

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

import valorantx2 as valorantx
from core.enums import Emoji

from . import __version__
from .db import DatabaseConnection
from .translator import Translator
from .tree import LatteMaidTree
from .utils.colorthief import ColorThief

if TYPE_CHECKING:
    from cogs.about import About as AboutCog
    from cogs.admin import Developer as DeveloperCog
    from cogs.jsk import Jishaku as JishakuCog
    from cogs.valorant import Valorant as ValorantCog

load_dotenv()

_log = logging.getLogger(__name__)

# jishaku
os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_HIDE'] = 'True'

description = "Hello, I'm latte maid, a bot made by discord: stacia.(240059262297047041)"

INITIAL_EXTENSIONS = (
    'cogs.about',
    'cogs.admin',
    'cogs.errors',
    'cogs.events',
    'cogs.help',
    'cogs.jsk',
    'cogs.stats',
    'cogs.test',
    'cogs.valorant',
    # 'cogs.ipc', # someday maybe
)


class LatteMaid(commands.AutoShardedBot):
    user: discord.ClientUser
    bot_app_info: discord.AppInfo
    tree: LatteMaidTree

    def __init__(
        self,
        debug_mode: bool = False,
        tree_sync_at_startup: bool = False,
    ) -> None:
        # intents
        intents = discord.Intents.none()
        intents.guilds = True
        intents.emojis_and_stickers = True
        # intents.dm_messages = True # TODO: implementation modmail?

        # allowed_mentions
        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, replied_user=False, users=True)

        super().__init__(
            command_prefix=[],
            help_command=None,
            allowed_mentions=allowed_mentions,
            case_insensitive=True,
            intents=intents,
            description=description,
            application_id=os.getenv('CLIENT_ID') if not debug_mode else os.getenv('CLIENT_ID_TEST'),
            tree_cls=LatteMaidTree,
            activity=discord.Activity(type=discord.ActivityType.listening, name='luna ♡ ₊˚'),
        )
        self._debug_mode: bool = debug_mode
        self._tree_sync_at_startup: bool = tree_sync_at_startup
        self._version: str = __version__
        self.emoji: type[Emoji] = Emoji
        self.support_guild_id: int = 1097859504906965042
        self.support_invite_url: str = 'https://discord.gg/mKysT7tr2v'
        # maintenance
        self._is_maintenance: bool = False
        self.maintenance_message: str = 'Bot is in maintenance mode.'
        self.maintenance_time: datetime.datetime | None = None
        # palette
        self.palettes: dict[str, list[discord.Colour]] = {}
        # database
        self.db: DatabaseConnection = DatabaseConnection(os.environ['DATABASE_URL' + ('_TEST' if debug_mode else '')])
        # valorant
        self.valorant_client: valorantx.Client = valorantx.Client(self)

    @property
    def owner(self) -> discord.User:
        """Returns the bot owner."""
        return self.bot_app_info.owner

    @property
    def support_guild(self) -> discord.Guild | None:
        if self.support_guild_id is None:
            raise ValueError('Support guild ID is not set.')
        return self.get_guild(self.support_guild_id)

    @property
    def version(self) -> str:
        return self._version

    @discord.utils.cached_property
    def traceback_log(self) -> discord.TextChannel | None:
        return self.get_channel(1102897424235761724)  # type: ignore

    def is_maintenance(self) -> bool:
        return self._is_maintenance

    def is_debug_mode(self) -> bool:
        return self._debug_mode

    def get_invite_url(self) -> str:
        scopes = ('bot', 'applications.commands')
        permissions = discord.Permissions(int(os.getenv('INVITE_PERMISSIONS', 280576)))
        return discord.utils.oauth_url(self.application_id, permissions=permissions, scopes=scopes)  # type: ignore

    # def get_oauth2_url(self) -> str:
    #     scopes = ('identify', 'guilds')
    #     return discord.utils.oauth_url(self.application_id, scopes=scopes)

    # @discord.utils.cached_property
    # def webhook(self) -> discord.Webhook:
    #     wh_id, wh_token = self.config.stat_webhook
    #     hook = discord.Webhook.partial(id=wh_id, token=wh_token, session=self.session)
    #     return hook

    # @discord.utils.cached_property
    # def traceback_log(self) -> Optional[Union[discord.abc.GuildChannel, discord.Thread, discord.abc.PrivateChannel]]:
    #     return self.get_channel(config.traceback_channel_id)

    def is_blocked(self, obj: discord.abc.User | discord.Guild | int, /) -> bool:
        obj_id = obj if isinstance(obj, int) else obj.id
        return self.db.get_blacklist(obj_id) is not None

    # bot extension setup

    async def tree_sync(self, guild_only: bool = False) -> None:
        # tree sync application commands
        if not guild_only:
            await self.tree.sync()
        sync_guilds = [
            self.support_guild_id,
            # 1042503061454729289,  # EMOJI ABILITY 2
            # 1042502960921452734,  # EMOJI ABILITY 1
            # 1043965050630705182,  # EMOJI TIER
            # 1042501718958669965,  # EMOJI AGENT
            # 1042809126624964651,  # EMOJI MATCH
        ]
        for guild_id in sync_guilds:
            try:
                await self.tree.sync(guild=discord.Object(id=guild_id))
            except Exception as e:
                _log.error(f'Failed to sync guild {guild_id}.', exc_info=e)

    async def cogs_load(self) -> None:
        """Load cogs."""
        await asyncio.gather(*[self.load_extension(extension) for extension in INITIAL_EXTENSIONS])

    async def cogs_unload(self) -> None:
        """Unload cogs."""
        await asyncio.gather(*[self.unload_extension(extension) for extension in INITIAL_EXTENSIONS])

    async def run_valorant_client(self) -> None:
        username = os.getenv('RIOT_USERNAME')
        password = os.getenv('RIOT_PASSWORD')

        if username is None or password is None:
            _log.warning('valorant client is not initialized due to missing credentials.')
            return

        try:
            await asyncio.wait_for(self.valorant_client.authorize(username, password), timeout=120)
        except asyncio.TimeoutError:
            _log.error('valorant client failed to initialize within 120 seconds.')
        except valorantx.RiotAuthenticationError as e:
            await self.valorant_client._init()  # bypass the auth check
            _log.warning('valorant client failed to authorized', exc_info=e)
        else:
            _log.info('valorant client is initialized.')

    async def setup_hook(self) -> None:
        # asyncio.get_running_loop().set_debug(self.is_debug_mode())

        self.session = aiohttp.ClientSession()

        self.translator = Translator(self)
        await self.tree.set_translator(self.translator)

        self.bot_app_info = await self.application_info()
        self.owner_ids = [self.bot_app_info.owner.id, 385049730222129152]

        # database
        await self.db.initialize()

        # load cogs
        await self.cogs_load()

        # tree sync
        if self._tree_sync_at_startup:
            await self.tree_sync()

        await self.tree.insert_model_to_commands()

        # valorant client
        # await self.run_valorant_client()
        # self.loop.create_task(self.run_valorant_client())

    # cogs property

    @property
    def about(self) -> AboutCog | None:
        return self.get_cog('about')  # type: ignore

    @property
    def jsk(self) -> JishakuCog | None:
        return self.get_cog('jishaku')  # type: ignore

    @property
    def developer(self) -> DeveloperCog | None:
        return self.get_cog('developer')  # type: ignore

    @property
    def valorant(self) -> ValorantCog | None:
        return self.get_cog('valorant')

    # bot event

    async def on_ready(self) -> None:
        if not hasattr(self, 'launch_time'):
            self.launch_time: datetime.datetime = datetime.datetime.now()

        if self.is_debug_mode():
            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.listening, name='latte maid is in debug mode'),
                status=discord.Status.idle,
            )
        _log.info(
            f'logged in as: {self.user} '
            + (f'activity: {self.activity.name} ' if self.activity is not None else '')
            + f'servers: {len(self.guilds)} '
            + f'users: {sum(guild.member_count for guild in self.guilds if guild.member_count is not None)}'
        )

    async def on_message(self, message: discord.Message, /) -> None:
        if message.author == self.user:
            return

        await self.process_commands(message)

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        _log.exception('Ignoring exception in %s', event_method)

    # palettes

    @overload
    def get_palettes(self, id: str, /, *, onlyone: Literal[True] = True) -> discord.Colour | None: ...

    @overload
    def get_palettes(self, id: str, /, *, onlyone: Literal[False] = False) -> list[discord.Colour] | None: ...

    def get_palettes(self, id: str, /, *, onlyone: bool = False) -> list[discord.Color] | discord.Colour | None:
        if id not in self.palettes:
            return None
        palettes = self.palettes[id]
        if onlyone:
            return random.choice(palettes)
        return palettes

    def store_palettes(self, id: str, color: list[discord.Colour]) -> list[discord.Colour]:
        self.palettes[id] = color
        return color

    async def fetch_palettes(
        self,
        id: str,
        image: discord.Asset | str,
        palette: int = 5,
        *,
        store: bool = True,
    ) -> list[discord.Colour]:
        palettes = self.get_palettes(id, onlyone=False)
        if palettes is not None:
            return palettes
        if not isinstance(image, discord.Asset):
            state = self._get_state()
            image = discord.Asset(state, url=str(image), key=id)
        file = await image.to_file(filename=id)
        to_bytes = file.fp
        if palette > 0:
            palettes = [discord.Colour.from_rgb(*c) for c in ColorThief(to_bytes).get_palette(color_count=palette)]
        else:
            palettes = [discord.Colour.from_rgb(*ColorThief(to_bytes).get_color())]
        if store:
            self.store_palettes(id, palettes)
        return palettes

    # bot methods

    async def load_extension(self, name: str, *, package: str | None = None) -> None:
        try:
            await super().load_extension(name, package=package)
        except Exception as e:
            _log.error('failed to load extension %s', name, exc_info=e)
            raise e
        else:
            _log.info('loaded extension %s', name)

    async def unload_extension(self, name: str, *, package: str | None = None) -> None:
        try:
            await super().unload_extension(name, package=package)
        except Exception as e:
            _log.error('failed to unload extension %s', name, exc_info=e)
            raise e
        else:
            _log.info('unloaded extension %s', name)

    async def reload_extension(self, name: str, *, package: str | None = None) -> None:
        try:
            await super().reload_extension(name, package=package)
        except Exception as e:
            _log.error('failed to reload extension %s', name, exc_info=e)
            raise e
        else:
            _log.info('reloaded extension %s', name)

    async def close(self) -> None:
        await self.cogs_unload()
        await self.session.close()
        await self.db.close()
        await self.valorant_client.close()
        await super().close()

    async def start(self) -> None:
        if self.is_debug_mode():
            token = os.getenv('DISCORD_TOKEN_TEST')
        else:
            token = os.getenv('DISCORD_TOKEN')
        if token is None:
            raise RuntimeError('No token provided.')
        await super().start(token=token, reconnect=True)
