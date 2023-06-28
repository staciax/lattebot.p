from __future__ import annotations

import contextlib
import logging
from abc import ABC
from typing import TYPE_CHECKING, List

import aiohttp
import discord
from discord import app_commands, ui
from discord.app_commands import Choice, locale_str as _T

import core.utils.chat_formatting as chat
import valorantx2 as valorantx
from core.checks import cooldown_long, cooldown_medium, cooldown_short, dynamic_cooldown
from core.cog import Cog
from core.errors import UserInputError
from core.i18n import I18n, cog_i18n
from core.ui.embed import MiadEmbed as Embed
from core.utils.database.models import User
from valorantx2.client import Client as ValorantClient
from valorantx2.errors import RiotMultifactorError
from valorantx2.utils import locale_converter

from .account_manager import AccountManager
from .admin import Admin
from .auth import RiotAuth
from .context_menu import ContextMenu
from .error import (
    ErrorHandler,
    RiotAuthAlreadyLinked,
    RiotAuthMaxLimitReached,
    RiotAuthMultiFactorTimeout,
    RiotAuthNotLinked,
)
from .events import Events
from .notify import Notify
from .ui import embeds as e
from .ui.modal import RiotMultiFactorModal
from .ui.views import (
    CarrierView,
    CollectionView,
    FeaturedBundleView,
    GamePassView,
    MissionView,
    NightMarketView,
    StoreFrontView,
    WalletView,
)
from .ui.views_7 import NewStoreFrontView

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2.client import Client as ValorantClient

_ = I18n('valorant', __file__)

_log = logging.getLogger(__name__)


# thanks for redbot
class CompositeMetaClass(type(Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


@cog_i18n(_)
class Valorant(Admin, ContextMenu, ErrorHandler, Events, Notify, Cog, metaclass=CompositeMetaClass):
    def __init__(self, bot: LatteMaid) -> None:
        self.bot: LatteMaid = bot

    @property
    def display_emoji(self) -> discord.Emoji | None:
        return self.bot.get_emoji(998169266044022875)

    @property
    def valorant_client(self) -> ValorantClient:
        return self.bot.valorant_client

    async def cog_load(self) -> None:
        # self.notify_alert.start()
        self.valorant_version_checker.start()
        self.valorant_cache_control.start()

    async def cog_unload(self) -> None:
        # self.notify_alert.cancel()
        self.valorant_version_checker.cancel()
        self.valorant_cache_control.cancel()

    # check

    async def interaction_check(self, interaction: discord.Interaction[LatteMaid]) -> bool:
        if await interaction.client.is_owner(interaction.user):
            return True
        if not self.valorant_client.is_ready():
            raise UserInputError(_('Valorant client is not ready. Please try again later.', interaction.locale))
        return super().interaction_check(interaction)

    # user

    async def get_user(self, id: int, /, *, check_linked: bool = True) -> User | None:
        user = await self.bot.db.get_user(id)

        if user is None:
            _log.info(f'User {id} not found in database.')
            return None

        if check_linked and len(user.riot_accounts) == 0:
            raise RiotAuthNotLinked(_('You have not linked any riot accounts.', user.locale))

        return user

    async def get_or_create_user(self, id: int, /, locale: discord.Locale) -> User:
        user = await self.get_user(id)
        if user is None:
            await self.bot.db.create_user(id, locale=locale)
            raise RiotAuthNotLinked(_('You have not linked any riot accounts.', locale))

        return user

    # app commands

    @app_commands.command(name=_T('login'), description=_T('Log in with your Riot accounts'))
    @app_commands.describe(username=_T('Input username'), password=_T('Input password'), region=_T('Select region'))
    @app_commands.rename(username=_T('username'), password=_T('password'), region=_T('region'))
    @app_commands.choices(
        region=[
            Choice(name=_T('Asia Pacific'), value='ap'),
            Choice(name=_T('Europe'), value='eu'),
            Choice(name=_T('North America / Latin America / Brazil'), value='na'),
            Choice(name=_T('Korea'), value='kr'),
        ]
    )
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def login(
        self,
        interaction: discord.Interaction[LatteMaid],
        username: app_commands.Range[str, 1, 24],
        password: app_commands.Range[str, 1, 128],
        region: Choice[str] | None = None,
    ) -> None:
        # TODO: transformers params
        # TODO: website login ?
        # TODO: TOS, privacy policy
        user = await self.get_user(interaction.user.id, check_linked=False)
        if user is None:
            user = await self.bot.db.create_user(interaction.user.id, locale=interaction.locale)

        if len(user.riot_accounts) >= 5:
            raise RiotAuthMaxLimitReached('You can only link up to 5 accounts.')

        riot_auth = RiotAuth()

        try:
            await riot_auth.authorize(username.strip(), password.strip(), remember=True)
        except RiotMultifactorError:
            multi_modal = RiotMultiFactorModal(riot_auth, interaction)
            await interaction.response.send_modal(multi_modal)
            await multi_modal.wait()

            if multi_modal.code is None:
                raise RiotAuthMultiFactorTimeout('You did not enter the code in time.')

            interaction = multi_modal.interaction or interaction

            if multi_modal.interaction is not None:
                await interaction.response.defer(ephemeral=True, thinking=True)

            try:
                await riot_auth.authorize_multi_factor(multi_modal.code, remember=True)
            except Exception as e:
                await multi_modal.on_error(interaction, e)
                return
            finally:
                multi_modal.stop()

        else:
            await interaction.response.defer(ephemeral=True)

        # check if already linked
        riot_account = await self.bot.db.get_riot_account_by_puuid_and_owner_id(
            puuid=riot_auth.puuid, owner_id=interaction.user.id
        )
        if riot_account is not None:
            raise RiotAuthAlreadyLinked('You already have this account linked.')

        # fetch userinfo and region
        try:
            await riot_auth.fetch_userinfo()
        except aiohttp.ClientResponseError as e:
            _log.error('riot auth error fetching userinfo', exc_info=e)

        # set region if specified
        if region is not None:
            riot_auth.region = region.value
        else:
            # fetch region if not specified
            try:
                await riot_auth.fetch_region()
            except aiohttp.ClientResponseError as e:
                riot_auth.region = 'ap'  # default to ap
                _log.error('riot auth error fetching region', exc_info=e)
        assert riot_auth.region is not None

        riot_account = await self.bot.db.create_riot_account(
            interaction.user.id,
            puuid=riot_auth.puuid,
            game_name=riot_auth.game_name,
            tag_line=riot_auth.tag_line,
            region=riot_auth.region,
            scope=riot_auth.scope,  # type: ignore
            token_type=riot_auth.token_type,  # type: ignore
            expires_at=riot_auth.expires_at,
            id_token=riot_auth.id_token,  # type: ignore
            access_token=riot_auth.access_token,  # type: ignore
            entitlements_token=riot_auth.entitlements_token,  # type: ignore
            ssid=riot_auth.get_ssid(),
            notify=False,
        )
        if not len(user.riot_accounts):
            await self.bot.db.update_user(user.id, main_account_id=riot_account.id)

        _log.info(
            f'{interaction.user}({interaction.user.id}) linked {riot_auth.display_name}({riot_auth.puuid}) - {riot_auth.region}'
        )
        # invalidate cache
        # self.??.invalidate(self, id=interaction.user.id)

        e = Embed(description=f'Successfully logged in {chat.bold(riot_auth.display_name)}')
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name=_T('logout'), description=_T('Logout and Delete your accounts from database'))
    @app_commands.rename(puuid=_T('account'))
    @app_commands.describe(puuid=_T('Select account to logout'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def logout(self, interaction: discord.Interaction[LatteMaid], puuid: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)

        e = Embed(description=f'Successfully logged out all accounts')

        if puuid is None:
            await self.bot.db.delete_all_riot_accounts(owner_id=interaction.user.id)
            _log.info(f'{interaction.user} logged out all accounts')
        else:
            puuid, riot_id = puuid.split(';')
            e.description = f'Successfully logged out account {chat.bold(riot_id)}'
            await self.bot.db.delete_riot_account(puuid=puuid, owner_id=interaction.user.id)
            _log.info(f'{interaction.user}({interaction.user.id}) logged out account {riot_id}({puuid})')

        await interaction.followup.send(embed=e, ephemeral=True)

        # # invalidate cache
        # self.fetch_user.invalidate(self, id=interaction.user.id)

    @logout.autocomplete('puuid')
    async def logout_autocomplete(
        self, interaction: discord.Interaction[LatteMaid], current: str
    ) -> List[app_commands.Choice[str]]:
        user = await self.bot.db.get_user(interaction.user.id)
        if user is None:
            return []

        if not len(user.riot_accounts):
            return [app_commands.Choice(name=_('You have no accounts linked.', interaction.locale), value="-")]

        return [
            app_commands.Choice(
                name=f'{account.game_name}#{account.tag_line}',
                value=account.puuid + ';' + f'{account.game_name}#{account.tag_line}',
            )
            for account in user.riot_accounts
        ]

    # TODO: remove defer first

    @app_commands.command(name=_T('store'), description=_T('Shows your daily store in your accounts'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def store(self, interaction: discord.Interaction[LatteMaid]) -> None:
        sf = await self.valorant_client.fetch_storefront()
        view = NewStoreFrontView(interaction, sf)
        await view.start()

        # user = await self.get_or_create_user(interaction.user.id, interaction.locale)
        # await interaction.response.defer()
        # view = StoreFrontView(interaction, AccountManager(user, self.bot))
        # await view.callback(interaction)

        # source = StoreFrontPageSource(user)
        # view = ValorantSwitchAccountView(source, interaction)
        # await view.start_valorant()

    @app_commands.command(name=_T('nightmarket'), description=_T('Show skin offers on the nightmarket'))
    @app_commands.rename(hide=_T('hide'))
    @app_commands.describe(hide=_T('Hide the skin offers'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def nightmarket(self, interaction: discord.Interaction[LatteMaid], hide: bool = False) -> None:
        user = await self.get_or_create_user(interaction.user.id, interaction.locale)
        await interaction.response.defer()
        view = NightMarketView(interaction, AccountManager(user, self.bot), hide)
        await view.callback(interaction)

    # @app_commands.command(name=_T('agent_store'), description=_T('Show the current featured agents'))
    # @app_commands.guild_only()
    # @dynamic_cooldown(cooldown_short)
    # async def agent_store(self, interaction: discord.Interaction[LatteMaid]) -> None:
    #     ...

    @app_commands.command(name=_T('bundles'), description=_T('Show the current featured bundles'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def bundles(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await interaction.response.defer()
        view = FeaturedBundleView(interaction, self.valorant_client)
        await view.start()

    @app_commands.command(name=_T('point'), description=_T('View your remaining Valorant and Riot Points (VP/RP)'))
    @app_commands.rename(private=_T('private'))
    @app_commands.describe(private=_T('Show the message only to you'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def point(self, interaction: discord.Interaction[LatteMaid], private: bool = True) -> None:
        user = await self.get_or_create_user(interaction.user.id, interaction.locale)
        await interaction.response.defer(ephemeral=private)
        view = WalletView(interaction, AccountManager(user, self.bot))
        await view.callback(interaction)

        # source = WalletPageSource(user)
        # view = ValorantSwitchAccountView(source, interaction)
        # await view.start_valorant()

    @app_commands.command(name=_T('battlepass'), description=_T('View your battlepass current tier'))
    @app_commands.rename(season=_T('season'))
    @app_commands.describe(season=_T('Select season to view'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def battlepass(self, interaction: discord.Interaction[LatteMaid], season: str | None = None) -> None:
        user = await self.get_or_create_user(interaction.user.id, interaction.locale)
        await interaction.response.defer()
        view = GamePassView(
            interaction,
            AccountManager(user, self.bot),
            valorantx.RelationType.season,
        )
        await view.callback(interaction)

    @app_commands.command(name=_T('eventpass'), description=_T('View your Eventpass current tier'))
    @app_commands.rename(event=_T('event'))
    @app_commands.describe(event=_T('Select event to view'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def eventpass(self, interaction: discord.Interaction[LatteMaid], event: str | None = None) -> None:
        user = await self.get_or_create_user(interaction.user.id, interaction.locale)
        await interaction.response.defer()
        view = GamePassView(
            interaction,
            AccountManager(user, self.bot),
            valorantx.RelationType.event,
        )
        await view.callback(interaction)

    @app_commands.command(name=_T('mission'), description=_T('View your daily/weekly mission progress'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def mission(self, interaction: discord.Interaction[LatteMaid]) -> None:
        user = await self.get_or_create_user(interaction.user.id, interaction.locale)
        await interaction.response.defer()
        view = MissionView(
            interaction,
            AccountManager(user, self.bot),
        )
        await view.callback(interaction)

    @app_commands.command(name=_T('collection'), description=_T('Shows your collection'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def collection(self, interaction: discord.Interaction[LatteMaid]) -> None:
        user = await self.get_or_create_user(interaction.user.id, interaction.locale)
        await interaction.response.defer()
        view = CollectionView(
            interaction,
            AccountManager(user, self.bot),
        )
        await view.callback(interaction)

    @app_commands.command(name=_T('agents'), description=_T('Agent Contracts'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def agents(self, interaction: discord.Interaction[LatteMaid]) -> None:
        user = await self.get_or_create_user(interaction.user.id, interaction.locale)
        await interaction.response.defer()
        view = GamePassView(
            interaction,
            AccountManager(user, self.bot),
            valorantx.RelationType.agent,
        )
        await view.callback(interaction)

    @app_commands.command(name=_T('carrier'), description=_T('Shows your carrier'))
    @app_commands.choices(
        mode=[
            Choice(name=_T('Unrated'), value='unrated'),
            Choice(name=_T('Competitive'), value='competitive'),
            Choice(name=_T('SwiftPlay'), value='swiftplay'),
            Choice(name=_T('Deathmatch'), value='deathmatch'),
            Choice(name=_T('Spike Rush'), value='spikerush'),
            Choice(name=_T('Team Deathmatch'), value='hurm'),
            Choice(name=_T('Escalation'), value='ggteam'),
            Choice(name=_T('Replication'), value='onefa'),
            Choice(name=_T('Snowball Fight'), value='snowball'),
            Choice(name=_T('Custom'), value='custom'),
        ]
    )
    @app_commands.describe(mode=_T('The queue to show your carrier for'))
    @app_commands.rename(mode=_T('mode'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_long)
    async def carrier(self, interaction: discord.Interaction[LatteMaid], mode: Choice[str] | None = None) -> None:
        user = await self.get_or_create_user(interaction.user.id, interaction.locale)

        await interaction.response.defer()
        queue = mode.value if mode is not None else None
        view = CarrierView(
            interaction,
            AccountManager(user, self.bot),
            queue,
        )
        await view.callback(interaction)

    @app_commands.command(name=_T('match'), description=_T('Shows latest match details'))
    @app_commands.choices(
        mode=[
            Choice(name=_T('Unrated'), value='unrated'),
            Choice(name=_T('Competitive'), value='competitive'),
            Choice(name=_T('SwiftPlay'), value='swiftplay'),
            Choice(name=_T('Deathmatch'), value='deathmatch'),
            Choice(name=_T('Spike Rush'), value='spikerush'),
            Choice(name=_T('Team Deathmatch'), value='hurm'),
            Choice(name=_T('Escalation'), value='ggteam'),
            Choice(name=_T('Replication'), value='onefa'),
            Choice(name=_T('Snowball Fight'), value='snowball'),
            Choice(name=_T('Custom'), value='custom'),
        ]
    )
    @app_commands.describe(mode=_T('The queue to show your latest match for'))
    @app_commands.rename(mode=_T('mode'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_medium)
    async def match(self, interaction: discord.Interaction, mode: Choice[str] | None = None) -> None:
        user = await self.get_or_create_user(interaction.user.id, interaction.locale)
        await interaction.response.defer()

    @app_commands.command(name=_T('patchnote'), description=_T('Patch notes'))
    @app_commands.guild_only()
    @dynamic_cooldown(cooldown_short)
    async def patchnote(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await interaction.response.defer()

        patch_notes = await self.valorant_client.fetch_patch_notes(locale_converter.to_valorant(interaction.locale))
        latest = patch_notes.get_latest_patch_note()
        if latest is not None:
            pns = await self.valorant_client.fetch_patch_note_from_site(latest.url)

            embed = e.patch_note_e(latest, pns.banner.url if pns.banner is not None else None)

            if embed.image.url is not None:
                with contextlib.suppress(Exception):
                    embed.colour = await self.bot.get_or_fetch_color(latest.uid, embed.image.url, 5)

            view = ui.View().add_item(
                ui.Button(
                    label=patch_notes.see_article_title,
                    url=latest.url,
                    emoji=str(self.bot.emoji.link_standard),
                )
            )

            await interaction.followup.send(embed=embed, view=view)

        else:
            raise UserInputError('Patch note not found')

    # infomation commands

    # @app_commands.command(name=_T('agent'), description=_T('View agent info'))
    # @app_commands.guild_only()
    # @app_commands.rename(agent='agent')
    # # @dynamic_cooldown(cooldown_short)
    # async def agent(self, interaction: discord.Interaction, agent: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('buddy'), description=_T('View buddy info'))
    # @app_commands.guild_only()
    # @app_commands.rename(buddy='buddy')
    # # @dynamic_cooldown(cooldown_short)
    # async def buddy(self, interaction: discord.Interaction, buddy: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('bundle'), description='inspect a specific bundle')
    # @app_commands.describe(bundle="The name of the bundle you want to inspect!")
    # @app_commands.rename(bundle=_T('bundle'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_short)
    # async def bundle(self, interaction: discord.Interaction, bundle: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('spray'), description=_T('View spray info'))
    # @app_commands.guild_only()
    # @app_commands.rename(spray='spray')
    # # @dynamic_cooldown(cooldown_short)
    # async def spray(self, interaction: discord.Interaction, spray: str | None = None) -> None:
    #     ...

    # player = app_commands.Group(name=_T('player'), description=_T('Player commands'), guild_only=True)

    # @player.command(name=_T('card'), description=_T('View player card'))
    # @app_commands.rename(card='card')
    # # @dynamic_cooldown(cooldown_short)
    # async def player_card(self, interaction: discord.Interaction, card: str | None = None) -> None:
    #     ...

    # @player.command(name=_T('title'), description=_T('View player title'))
    # @app_commands.rename(title='title')
    # # @dynamic_cooldown(cooldown_short)
    # async def player_title(self, interaction: discord.Interaction) -> None:
    #     ...

    # @app_commands.command(name=_T('weapon'), description=_T('View weapon info'))
    # @app_commands.guild_only()
    # @app_commands.rename(weapon='weapon')
    # # @dynamic_cooldown(cooldown_short)
    # async def weapon(self, interaction: discord.Interaction, weapon: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('skin'), description=_T('View skin info'))
    # @app_commands.guild_only()
    # @app_commands.rename(skin='skin')
    # # @dynamic_cooldown(cooldown_short)
    # async def skin(self, interaction: discord.Interaction, skin: str | None = None) -> None:
    #     ...

    # auto complete
    # @bundle.autocomplete('bundle')
    # @agent.autocomplete('agent')
    # @buddy.autocomplete('buddy')
    # @spray.autocomplete('spray')
    # @weapon.autocomplete('weapon')
    # @skin.autocomplete('skin')
    # @player_card.autocomplete('card')
    # @player_title.autocomplete('title')
    # @battlepass.autocomplete('season')
    # @eventpass.autocomplete('event')
    # async def get_all_auto_complete(self, interaction: Interaction, current: str) -> List[Choice[str]]:

    #     locale = self.v_locale(interaction.locale)

    #     results: List[Choice[str]] = []
    #     mex_index = 25

    #     # TODO: cache choices

    #     if interaction.command is self.bundle:

    #         bundle_list = self.get_all_bundles()
    #         namespace = interaction.namespace.bundle
    #         mex_index = 15

    #         for bundle in sorted(bundle_list, key=lambda a: a.name_localizations.from_locale(str(locale))):
    #             if bundle.name_localizations.from_locale(str(locale)).lower().startswith(namespace.lower()):

    #                 bundle_name = bundle.name_localizations.from_locale(str(locale))

    #                 index = 2
    #                 for choice in results:
    #                     if choice.name.startswith(bundle_name):
    #                         bundle_name = f"{bundle_name} {index}"
    #                         index += 1

    #                 results.append(app_commands.Choice(name=bundle_name, value=bundle.uuid))
    #                 if len(results) >= mex_index:
    #                     break

    #     elif interaction.command is self.battlepass:

    #         value_list = self.get_all_seasons()
    #         namespace = interaction.namespace.season

    #         for value in sorted(value_list, key=lambda a: a.start_time):
    #             if value.name_localizations.from_locale(str(locale)).lower().startswith(namespace.lower()):

    #                 parent = value.parent
    #                 parent_name = ''
    #                 if parent is None:
    #                     if value.uuid != '0df5adb9-4dcb-6899-1306-3e9860661dd3':  # closed beta
    #                         continue
    #                 else:
    #                     parent_name = parent.name_localizations.from_locale(str(locale)) + ' '

    #                 value_name = parent_name + value.name_localizations.from_locale(str(locale))

    #                 if value_name == ' ':
    #                     continue

    #                 if not value_name.startswith('.') and not namespace.startswith('.'):
    #                     results.append(Choice(name=value_name, value=value.uuid))
    #                 elif namespace.startswith('.'):
    #                     results.append(Choice(name=value_name, value=value.uuid))

    #             if len(results) >= mex_index:
    #                 break

    #     else:

    #         if interaction.command is self.agent:
    #             value_list = self.get_all_agents()
    #             namespace = interaction.namespace.agent
    #         elif interaction.command is self.buddy:
    #             value_list = self.get_all_buddies()
    #             namespace = interaction.namespace.buddy
    #         elif interaction.command is self.spray:
    #             value_list = self.get_all_sprays()
    #             namespace = interaction.namespace.spray
    #         elif interaction.command is self.weapon:
    #             value_list = self.get_all_weapons()
    #             namespace = interaction.namespace.weapon
    #         elif interaction.command is self.skin:
    #             value_list = self.get_all_skins()
    #             namespace = interaction.namespace.skin
    #         elif interaction.command is self.player_card:
    #             value_list = self.get_all_player_cards()
    #             namespace = interaction.namespace.card
    #         elif interaction.command is self.player_title:
    #             value_list = self.get_all_player_titles()
    #             namespace = interaction.namespace.title
    #         elif interaction.command is self.eventpass:
    #             value_list = self.get_all_events()
    #             namespace = interaction.namespace.event
    #         else:
    #             return []

    #         for value in sorted(value_list, key=lambda a: a.name_localizations.from_locale(str(locale))):
    #             if value.name_localizations.from_locale(str(locale)).lower().startswith(namespace.lower()):

    #                 value_name = value.name_localizations.from_locale(str(locale))

    #                 if value_name == ' ':
    #                     continue

    #                 if not value_name.startswith('.') and not namespace.startswith('.'):
    #                     results.append(Choice(name=value_name, value=value.uuid))
    #                 elif namespace.startswith('.'):
    #                     results.append(Choice(name=value_name, value=value.uuid))

    #             if len(results) >= mex_index:
    #                 break

    #     return results[:mex_index]

    # develeping commands

    # @app_commands.command(name=_T('stats'), description=_T('Show the stats of a player'))
    # @app_commands.choices(
    #     queue=[
    #         Choice(name=_T('Unrated'), value='unrated'),
    #         Choice(name=_T('Competitive'), value='competitive'),
    #         Choice(name=_T('Deathmatch'), value='deathmatch'),
    #         Choice(name=_T('Spike Rush'), value='spikerush'),
    #         Choice(name=_T('Escalation'), value='escalation'),
    #         Choice(name=_T('Replication'), value='replication'),
    #         Choice(name=_T('Snowball Fight'), value='snowball'),
    #         Choice(name=_T('Custom'), value='custom'),
    #     ]
    # )
    # @app_commands.describe(queue=_T('Choose the queue'))
    # @app_commands.rename(queue=_T('queue'))
    # @dynamic_cooldown(cooldown_short)
    # @app_commands.guild_only()
    # async def stats(self, interaction: Interaction, queue: Choice[str] = "null") -> None:
    #     await interaction.response.defer()

    # @app_commands.describe(queue=_T('Party commands'))
    # @dynamic_cooldown(cooldown_short)
    # @app_commands.guild_only()
    # async def party(self, interaction: Interaction) -> None:
    #     await interaction.response.defer()

    # party = app_commands.Group(name=_T('party'), description=_T('Party commands'), guild_only=True)
    #
    # @party.command(name=_T('invite'), description=_T('Invite a player to your party'))
    # @dynamic_cooldown(cooldown_short)
    # async def party_invite(self, interaction: Interaction, player: discord.User) -> None:
    #     ...
    #
    # @party.command(name=_T('invite_by_name'), description=_T('Invite a player to your party by name'))
    # @dynamic_cooldown(cooldown_short)
    # async def party_invite_by_name(self, interaction: Interaction, player: str) -> None:
    #     ...
    #
    # @party.command(name=_T('kick'), description=_T('Kick a player from your party'))
    # @dynamic_cooldown(cooldown_short)
    # async def party_kick(self, interaction: Interaction, player: discord.User) -> None:
    #     ...
    #
    # @party.command(name=_T('leave'), description=_T('Leave your party'))
    # @dynamic_cooldown(cooldown_short)
    # async def party_leave(self, interaction: Interaction) -> None:
    #     ...
