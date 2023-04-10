from __future__ import annotations

import asyncio
import datetime
import io
import logging
import os
import traceback
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional, Tuple, Type, Union

import aiohttp

# import config
import discord

# import valorantx
from discord import app_commands
from discord.ext import commands
from discord.utils import MISSING
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from utils.config import Config
from utils.encryption import Encryption
from utils.enums import CDN, Emoji, Theme

from .i18n import Translator, _
from .tree import LatteTreeMaid
from .utils.colorthief import ColorThief

# from utils.ui import interaction_error_handler

if TYPE_CHECKING:
    from cogs.about import About
    from cogs.admin import Developer
    from cogs.jsk import Jishaku
    from cogs.valorant import Valorant

load_dotenv()

_log = logging.getLogger('latte_maid')

# jishaku
os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_HIDE'] = 'True'

description = 'Hello, I\'m latte, a bot made by @ꜱᴛᴀᴄɪᴀ.#7475 (240059262297047041)'

INITIAL_EXTENSIONS: Tuple[str, ...] = (
    'cogs.jsk',
    'cogs.admin',
    'cogs.events',
    'cogs.help',
    'cogs.about',
    # 'cogs.valorant',
    # 'cogs.role_connection',
    # 'cogs.ipc',
    # 'cogs.test',
)


class LatteMaid(commands.AutoShardedBot):
    if TYPE_CHECKING:
        tree: LatteTreeMaid

    db_session: async_sessionmaker[AsyncSession]
    db_engine: AsyncEngine
    bot_app_info: discord.AppInfo
    valorant_client: valorantx.Client

    def __init__(self) -> None:
        # intents
        intents = discord.Intents.default()
        intents.typing = False  # guild_typing and dm_typing

        # allowed_mentions
        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True, replied_user=True)

        super().__init__(
            command_prefix=commands.when_mentioned,
            help_command=None,
            allowed_mentions=allowed_mentions,
            case_insensitive=True,
            intents=intents,
            description=description,
            application_id=config.client_id,
            tree_cls=LatteTreeMaid,
            activity=discord.Activity(type=discord.ActivityType.listening, name='nyanpasu ♡ ₊˚'),
        )

        # bot stuff
        # self.launch_time: str = f'<t:{round(datetime.datetime.now().timestamp())}:R>'
        self._debug: bool = False
        self._version: str = '1.0.0a'

        # assets
        self.theme: Type[Theme] = Theme
        self.emoji: Type[Emoji] = Emoji
        self.cdn: Type[CDN] = CDN

        # bot invite link
        self._permission_invite: int = 280576
        self.invite_url = discord.utils.oauth_url(
            self.application_id or self.config.application_id,
            permissions=discord.Permissions(self._permission_invite),
        )

        # support guild
        self.support_guild_id: int = config.guild_id
        self.support_invite_url: str = 'https://discord.gg/xeVJYRDY'

        # oauth2
        self.linked_role_uri: str = 'http://localhost:8000/v1/linked-role'

        # maintenance
        self._is_maintenance: bool = False
        self.maintenance_message: str = _('Bot is in maintenance mode.')
        self.maintenance_time: Optional[datetime.datetime] = None

        # encryption
        self.encryption: Encryption = Encryption(config.cryptography)

        # i18n
        self.translator: Translator = MISSING

        # http session
        self.session: aiohttp.ClientSession = MISSING

        # app commands
        self._app_commands: Dict[str, Union[app_commands.AppCommand, app_commands.AppCommandGroup]] = {}

        # valorantx
        self.riot_username: str = config.riot_username
        self.riot_password: str = config.riot_password

        # config
        self.blacklist: Config[bool] = Config('blacklist.json')

        # colour
        self.colors: Dict[str, List[discord.Colour]] = {}

    @property
    def owner(self) -> discord.User:
        """Returns the bot owner."""
        return self.bot_app_info.owner

    @property
    async def dev(self) -> Optional[discord.User]:
        """Returns discord.User of the owner"""
        return await self.fetch_user(self.owner_id)  # type: ignore

    @property
    def support_guild(self) -> Optional[discord.Guild]:
        if self.support_guild_id is None:
            raise ValueError('Support guild ID is not set.')
        return self.get_guild(self.support_guild_id)

    @discord.utils.cached_property
    def webhook(self) -> discord.Webhook:
        wh_id, wh_token = self.config.stat_webhook
        hook = discord.Webhook.partial(id=wh_id, token=wh_token, session=self.session)
        return hook

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

    async def setup_hook(self) -> None:
        # session
        if self.session is MISSING:
            self.session = aiohttp.ClientSession()

        # i18n
        if self.translator is MISSING:
            self.translator = Translator(self, './lattemid/i18n')
            await self.tree.set_translator(self.translator)

        # bot info
        self.bot_app_info = await self.application_info()
        self.owner_id = self.bot_app_info.owner.id

        # localizations
        self.translator.load_string_localize()

        # valorantx
        # self.valorant_client = valorantx.Client()
        # self.loop.create_task(self.valorant_client.login(self.riot_username, self.riot_password))

        # load cogs
        await self.cogs_load()

        # tree translator app commands
        # tree_app_commands = self.tree.get_commands()
        # for command in tree_app_commands:
        #     await command.get_translated_payload(self.translator)

        # tree sync application commands
        await self.tree.sync()
        sync_guilds = [
            # self.support_guild_id,
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

        await Translator.get_i18n(
            cogs=self.cogs,
            excludes=['developer', 'jishaku'],  # exclude cogs
            only_public=True,  # exclude @app_commands.guilds()
            set_locale=[discord.Locale.american_english, discord.Locale.thai],  # locales to create
        )

        await self.fetch_app_commands()

    async def on_ready(self) -> None:
        if not hasattr(self, 'launch_time'):
            self.launch_time: datetime.datetime = datetime.datetime.now()
            # self.launch_time: str = f'<t:{round(datetime.datetime.now().timestamp())}:R>'

        _log.info(
            f'logged in as: {self.user} '
            + (f'activity: {self.activity.name} ' if self.activity is not None else '')
            + f'servers: {len(self.guilds)} '
            + f'users: {sum(guild.member_count for guild in self.guilds if guild.member_count is not None)}'
        )
        if self.is_debug():
            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.listening, name='latte maid is in debug mode'),
                status=discord.Status.idle,
            )

    async def on_message(self, message: discord.Message, /) -> None:
        if message.author == self.user:
            return

        await self.process_commands(message)

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        _log.exception('Ignoring exception in %s', event_method)

    @discord.utils.cached_property
    def traceback_log(self) -> Optional[Union[discord.abc.GuildChannel, discord.Thread, discord.abc.PrivateChannel]]:
        return self.get_channel(config.traceback_channel_id)

    async def add_to_blacklist(self, object_id: int):
        await self.blacklist.put(object_id, True)

    async def remove_from_blacklist(self, object_id: int):
        try:
            await self.blacklist.remove(object_id)
        except KeyError:
            pass

    @property
    def about(self) -> Optional[About]:
        return self.get_cog('about')

    @property
    def developer(self) -> Optional[Developer]:
        return self.get_cog('developer')

    @property
    def valorant(self) -> Optional[Valorant]:
        return self.get_cog('valorant')

    @property
    def jsk(self) -> Optional[Jishaku]:
        return self.get_cog('jishaku')

    async def get_db_session(self) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
        try:
            yield self.db_session
        except SQLAlchemyError as e:
            _log.exception(e)

    # https://github.com/Rapptz/RoboDanny/blob/5a9c02560048d5605701be4835e8d4ef2407c646/bot.py#L226
    async def get_or_fetch_member(self, guild: discord.Guild, member_id: int) -> Optional[discord.Member]:
        """Looks up a member in cache or fetches if not found.
        Parameters
        -----------
        guild: Guild
            The guild to look in.
        member_id: int
            The member ID to search for.
        Returns
        ---------
        Optional[Member]
            The member or None if not found.
        """

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard: discord.ShardInfo = self.get_shard(guild.shard_id)  # type: ignore  # will never be None
        if shard.is_ws_ratelimited():
            try:
                member = await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None
            else:
                return member

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

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

    def get_colors(self, id: str) -> List[discord.Colour]:
        """Returns the colors of the image."""
        if id in self.colors:
            return self.colors[id]
        return []

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

    def is_maintenance(self) -> bool:
        return self._is_maintenance

    def is_debug(self) -> bool:
        return self._debug

    # @property
    # def version(self) -> str:
    #     return self._version

    # @version.setter
    # def version(self, value: str) -> None:
    #     self._version = value

    @property
    def config(self):
        return __import__('config')

    async def close(self) -> None:
        await self.cogs_unload()
        await self.db_engine.dispose()
        await self.session.close()
        await self.valorant_client.close()
        await super().close()

    async def start(self) -> None:
        await super().start(token=config.token, reconnect=True)
