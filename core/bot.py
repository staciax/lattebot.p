from __future__ import annotations

import asyncio
import datetime
import logging
import os
import random
import traceback
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, Union

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import MISSING
from dotenv import load_dotenv

import valorantx2 as valorantx
from core.utils.enums import Emoji

from .database import DatabaseConnection

# from .i18n import I18n, _
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

description = 'Hello, I\'m latte, a bot made by @ꜱᴛᴀᴄɪᴀ.#7475 (240059262297047041)'

INITIAL_EXTENSIONS: Tuple[str, ...] = (
    'cogs.about',
    'cogs.admin',
    'cogs.errors',
    # 'cogs.events',
    'cogs.help',
    # 'cogs.jsk',
    # 'cogs.stats',
    'cogs.valorant',
    # 'cogs.ipc',
    'cogs.test',
)


class LatteMaid(commands.AutoShardedBot):
    if TYPE_CHECKING:
        tree: LatteMaidTree

    db: DatabaseConnection
    bot_app_info: discord.AppInfo

    def __init__(
        self,
        debug_mode: bool = False,
        tree_sync_at_startup: bool = False,
    ) -> None:
        # intents
        intents = discord.Intents.none()  # set all intents to False
        intents.guilds = True
        # intents.dm_messages = True # wait for implementation modmail?

        # allowed_mentions
        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True, replied_user=True)

        super().__init__(
            command_prefix=commands.when_mentioned,
            help_command=None,
            allowed_mentions=allowed_mentions,
            case_insensitive=True,
            intents=intents,
            description=description,
            application_id=os.getenv('CLIENT_ID'),
            tree_cls=LatteMaidTree,
            activity=discord.Activity(type=discord.ActivityType.listening, name='nyanpasu ♡ ₊˚'),
        )

        # config
        self._debug_mode: bool = debug_mode
        self._tree_sync_at_startup: bool = tree_sync_at_startup
        self._version: str = '1.0.0a'

        # assets
        self.emoji: Type[Emoji] = Emoji

        # support guild
        self.support_guild_id: int = 1097859504906965042
        self.support_invite_url: str = 'https://discord.gg/mKysT7tr2v'

        # maintenance
        self._is_maintenance: bool = False
        self.maintenance_message: str = 'Bot is in maintenance mode.'
        self.maintenance_time: Optional[datetime.datetime] = None

        # i18n
        self.translator: Translator = MISSING

        # http session
        self.session: aiohttp.ClientSession = MISSING

        # app commands
        self._app_commands: Dict[str, Union[app_commands.AppCommand, app_commands.AppCommandGroup]] = {}

        # colour
        self.colors: Dict[str, List[discord.Colour]] = {}

        # encryption
        # self.encryption: Encryption = Encryption(config.cryptography)

        # database
        self.db: DatabaseConnection = DatabaseConnection(os.getenv('DATABASE_URI_TEST'))  # type: ignore TODO: debug mode check and change

        # valorant
        self.valorant_client: valorantx.Client = valorantx.Client(self)

    @property
    def owner(self) -> discord.User:
        """Returns the bot owner."""
        return self.bot_app_info.owner

    @property
    def support_guild(self) -> Optional[discord.Guild]:
        if self.support_guild_id is None:
            raise ValueError('Support guild ID is not set.')
        return self.get_guild(self.support_guild_id)

    @discord.utils.cached_property
    def traceback_log(self) -> Optional[discord.TextChannel]:
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
                _log.exception(f'Failed to sync guild {guild_id}.')

    async def cogs_load(self) -> None:
        """Load cogs."""
        cogs = await asyncio.gather(
            *[self.load_extension(extension) for extension in INITIAL_EXTENSIONS], return_exceptions=True
        )
        [traceback.print_exception(c) for c in cogs if isinstance(c, commands.errors.ExtensionError)]

    async def cogs_unload(self) -> None:
        """Unload cogs."""
        cogs = await asyncio.gather(
            *[self.unload_extension(extension) for extension in INITIAL_EXTENSIONS], return_exceptions=True
        )
        [traceback.print_exception(c) for c in cogs if isinstance(c, commands.errors.ExtensionError)]

    async def _run_valorant_client(self) -> None:
        try:
            await asyncio.wait_for(self.valorant_client.authorize('ragluxs', '4869_lucky'), timeout=60)
        except asyncio.TimeoutError:
            _log.error('valorant client failed to initialize within 60 seconds.')
        except valorantx.RiotAuthenticationError as e:
            await self.valorant_client._init()  # bypass the auth check
            _log.warning(f'valorant client failed to authorized', exc_info=e)
        else:
            _log.info('valorant client is initialized.')

    async def setup_hook(self) -> None:
        # session
        if self.session is MISSING:
            self.session = aiohttp.ClientSession()

        # i18n
        if self.translator is MISSING:
            self.translator = Translator(self)
            await self.tree.set_translator(self.translator)

        # bot info
        self.bot_app_info = await self.application_info()
        self.owner_id = self.bot_app_info.owner.id

        # valorant client
        # await self._run_valorant_client()

        # valorantx
        # self.valorant_client = valorantx.Client()
        # self.loop.create_task(self.valorant_client.login(self.riot_username, self.riot_password))

        # load cogs
        await self.cogs_load()

        # tree sync
        if self._tree_sync_at_startup:
            await self.tree_sync()

        # tree translator app commands
        # tree_app_commands = self.tree.get_commands()
        # for command in tree_app_commands:
        #     await command.get_translated_payload(self.translator)

        # if os.environ.get('I18N') == 'True':
        #     await self.translator.get_i18n(
        #         excludes=['developer', 'jishaku'],  # exclude cogs
        #         only_public=True,  # exclude @app_commands.guilds()
        #         replace=True,
        #         set_locale=[
        #             discord.Locale.american_english,
        #             discord.Locale.thai,
        #         ],
        #     )

        await self.fetch_app_commands()

    # cogs property

    @property
    def about(self) -> Optional[AboutCog]:
        return self.get_cog('about')  # type: ignore

    @property
    def jsk(self) -> Optional[JishakuCog]:
        return self.get_cog('jishaku')  # type: ignore

    @property
    def developer(self) -> Optional[DeveloperCog]:
        return self.get_cog('developer')  # type: ignore

    @property
    def valorant(self) -> Optional[ValorantCog]:
        return self.get_cog('valorant')  # type: ignore

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

    # @discord.utils.cached_property
    # def traceback_log(self) -> Optional[Union[discord.abc.GuildChannel, discord.Thread, discord.abc.PrivateChannel]]:
    #     return self.get_channel(config.traceback_channel_id)

    # app commands

    async def fetch_app_commands(self) -> List[Union[app_commands.AppCommand, app_commands.AppCommandGroup]]:
        """Fetch all application commands."""

        app_commands_list = await self.tree.fetch_commands()

        for fetch in app_commands_list:
            if fetch.type == discord.AppCommandType.chat_input:
                if len(fetch.options) > 0:
                    self._app_commands[fetch.name] = fetch
                    for option in fetch.options:
                        if isinstance(option, app_commands.AppCommandGroup):
                            self._app_commands[option.qualified_name] = option
                else:
                    self._app_commands[fetch.name] = fetch

        return list(self._app_commands.values())

    def get_app_command(self, name: str) -> Optional[Union[app_commands.AppCommand, app_commands.AppCommandGroup]]:
        return self._app_commands.get(name)

    def get_app_commands(self) -> List[Union[app_commands.AppCommand, app_commands.AppCommandGroup]]:
        return sorted(list(self._app_commands.values()), key=lambda c: c.name)

    # colors

    # TODO: overload

    def get_colors(self, id: str, /) -> Optional[List[discord.Colour]]:
        """Returns the colors of the image."""
        if id in self.colors:
            return self.colors[id]
        return None

    def get_color(self, id: str, /) -> Optional[discord.Colour]:
        """Returns the color of the image."""
        colors = self.get_colors(id)
        if colors is not None:
            return random.choice(colors)
        return None

    def store_colors(self, id: str, color: List[discord.Colour]) -> List[discord.Colour]:
        """Sets the colors of the image."""
        self.colors[id] = color
        return color

    async def get_or_fetch_colors(
        self,
        id: str,
        image: Union[discord.Asset, str],
        palette: int = 0,
    ) -> List[discord.Colour]:
        """Returns the colors of the image."""
        colors = self.get_colors(id)
        if colors is not None:
            return colors
        if not isinstance(image, discord.Asset):
            state = self._get_state()
            image = discord.Asset(state, url=str(image), key=id)
        file = await image.to_file(filename=id)
        to_bytes = file.fp
        if palette > 0:
            colors = [discord.Colour.from_rgb(*c) for c in ColorThief(to_bytes).get_palette(color_count=palette)]
        else:
            colors = [discord.Colour.from_rgb(*ColorThief(to_bytes).get_color())]
        return self.store_colors(id, colors)

    async def get_or_fetch_color(
        self,
        id: str,
        image: Union[discord.Asset, str],
        palette: int = 0,
    ) -> discord.Colour:
        """Returns a random color of the image."""
        colors = await self.get_or_fetch_colors(id, image, palette)
        return random.choice(colors)

    # bot methods

    async def load_extension(self, name: str, *, package: Optional[str] = None) -> None:
        try:
            await super().load_extension(name, package=package)
        except Exception as e:
            _log.error('failed to load extension %s', name, exc_info=e)
            raise e
        else:
            _log.info('loaded extension %s', name)

    async def unload_extension(self, name: str, *, package: Optional[str] = None) -> None:
        try:
            await super().unload_extension(name, package=package)
        except Exception as e:
            _log.error('failed to unload extension %s', name, exc_info=e)
            raise e
        else:
            _log.info('unloaded extension %s', name)

    async def reload_extension(self, name: str, *, package: Optional[str] = None) -> None:
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
            token = os.getenv('DISCORD_TOKEN_DEBUG')
        else:
            token = os.getenv('DISCORD_TOKEN')
        if token is None:
            raise RuntimeError('No token provided.')
        await super().start(token=token, reconnect=True)
