from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, List

import aiohttp
import discord
import valorantx2 as valorantx
from discord import app_commands
from discord.app_commands import Choice, locale_str as _T

# from valorantx2.auth import RiotAuth
from valorantx2.errors import RiotMultifactorError

import core.utils.chat_formatting as chat

from .abc import ValorantCog
from .ui.views import StoreSwitchView
from .valorantx2_custom import Client as ValorantClient

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__name__)


class Valorant(ValorantCog):
    def __init__(self, bot: LatteMaid) -> None:
        self.bot: LatteMaid = bot
        self.v_client: ValorantClient = ValorantClient()

    @property
    def display_emoji(self) -> discord.Emoji | None:
        return self.bot.get_emoji(998169266044022875)

    async def run(self) -> None:
        try:
            await asyncio.wait_for(self.v_client.init(), timeout=30)
        except asyncio.TimeoutError:
            _log.error('Valorant API Client failed to initialize within 30 seconds.')
        else:
            _log.info('Valorant API Client is ready.')
            await self.v_client.authorize('ragluxs', '4869_lucky')
            # self.bot.dispatch('v_client_ready')

    async def cog_load(self) -> None:
        _log.info('Loading Valorant API Client...')
        self.bot.loop.create_task(self.run())

    async def cog_unload(self) -> None:
        await self.v_client.close()

    @app_commands.command(name=_T('login'), description=_T('Log in with your Riot accounts'))
    # @app_commands.describe(username=_T('Input username'), password=_T('Input password'))
    # @app_commands.rename(username=_T('username'), password=_T('password'))
    # @app_commands.guild_only()
    # @dynamic_cooldown(cooldown_5s)
    async def login(
        self,
        interaction: discord.Interaction,
        username: app_commands.Range[str, 1, 24],
        password: app_commands.Range[str, 1, 128],
    ) -> None:
        # TODO: transformers params
        # TODO: website login ?
        # TODO: TOS, privacy policy

        # try_auth = RiotAuth()

        try:
            await self.v_client.authorize(username.strip(), password.strip())  # remember=True
        except RiotMultifactorError:
            ...
            # wait_modal = RiotMultiFactorModal(try_auth)
            # await interaction.response.send_modal(wait_modal)
            # await wait_modal.wait()

            # # when timeout
            # if wait_modal.code is None:
            #     raise CommandError('You did not enter the code in time.')
            # try:
            #     await try_auth.authorize_multi_factor(wait_modal.code, remember=True)
            # except Exception as e:
            #     raise CommandError('Invalid Multi-factor code.') from e

            # interaction = wait_modal.interaction
            # await interaction.response.defer(ephemeral=True)
            # wait_modal.stop()

        except valorantx.RiotAuthenticationError as e:
            print(e)
            # raise CommandError('Invalid username or password.') from e
        except aiohttp.ClientResponseError as e:
            print(e)
            # raise CommandError('Riot server is currently unavailable.') from e
        else:
            await interaction.response.defer(ephemeral=True)

        # if v_user is None:
        #     try_auth.acc_num = 1
        #     v_user = self.set_valorant_user(interaction.user.id, interaction.guild_id, interaction.locale, try_auth)
        # else:
        #     for auth_u in v_user.get_riot_accounts():
        #         if auth_u.puuid == try_auth.puuid:
        #             raise CommandError('You already have this account linked.')
        #     self.add_riot_auth(interaction.user.id, try_auth)

        # payload = list(riot_auth.to_dict() for riot_auth in v_user.get_riot_accounts())
        # payload = self.bot.encryption.encrypt(json.dumps(payload))  # encrypt

        # await self.db.upsert_user(
        #     payload,
        #     interaction.user.id,
        #     interaction.guild_id or interaction.user.id,
        #     interaction.locale,
        # )

        # invalidate cache
        # try:
        #     self.fetch_user.invalidate(self, id=interaction.user.id)
        # except:
        #     pass

        e = discord.Embed(description=f"Successfully logged in {chat.bold(self.v_client.me.display_name)}")
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name=_T('logout'), description=_T('Logout and Delete your accounts from database'))
    @app_commands.rename(number=_T('account'))
    @app_commands.guild_only()
    # @dynamic_cooldown(cooldown_5s)
    async def logout(self, interaction: discord.Interaction[LatteMaid], number: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)

        e = discord.Embed(description=f"Successfully logged out all accounts")
        await interaction.followup.send(embed=e, ephemeral=True)

        # # invalidate cache
        # self.fetch_user.invalidate(self, id=interaction.user.id)

    @logout.autocomplete('number')
    async def logout_autocomplete(
        self, interaction: discord.Interaction[LatteMaid], current: str
    ) -> List[app_commands.Choice[str]]:
        # get_user = self._get_user(interaction.user.id)
        # if get_user is None:
        return [
            app_commands.Choice(name="You have no accounts linked.", value="-"),
        ]
        # return [
        #     app_commands.Choice(name=f"{user.acc_num}. {user.display_name} ", value=str(user.acc_num))
        #     for user in sorted(get_user.get_riot_accounts(), key=lambda x: x.acc_num)
        # ]

    @app_commands.command(name=_T('store'), description=_T('Shows your daily store in your accounts'))
    @app_commands.guild_only()
    # @dynamic_cooldown(cooldown_5s)
    async def store(self, interaction: discord.Interaction[LatteMaid]) -> None:
        await interaction.response.defer()
        view = StoreSwitchView(interaction, self.v_client)
        await view.start()

    # @app_commands.command(name=_T('nightmarket'), description=_T('Show skin offers on the nightmarket'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def nightmarket(self, interaction: discord.Interaction) -> None:
    #     ...

    # @app_commands.command(name=_T('battlepass'), description=_T('View your battlepass current tier'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def battlepass(self, interaction: discord.Interaction, season: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('eventpass'), description=_T('View your Eventpass current tier'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def eventpass(self, interaction: discord.Interaction, event: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('point'), description=_T('View your remaining Valorant and Riot Points (VP/RP)'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def point(self, interaction: discord.Interaction) -> None:
    #     ...

    # @app_commands.command(name=_T('bundles'), description=_T('Show the current featured bundles'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def bundles(self, interaction: discord.Interaction) -> None:
    #     ...

    # @app_commands.command(name=_T('mission'), description=_T('View your daily/weekly mission progress'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def mission(self, interaction: discord.Interaction) -> None:
    #     ...

    # @app_commands.command(name=_T('collection'), description=_T('Shows your collection'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def collection(self, interaction: discord.Interaction) -> None:
    #     ...

    # @app_commands.command(name=_T('agents'), description=_T('Agent Contracts'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def agents(self, interaction: discord.Interaction) -> None:
    #     await interaction.response.defer()
    #     ...

    # @app_commands.command(name=_T('carrier'), description=_T('Shows your carrier'))
    # @app_commands.choices(
    #     mode=[
    #         Choice(name=_T('Unrated'), value='unrated'),
    #         Choice(name=_T('Competitive'), value='competitive'),
    #         Choice(name=_T('SwiftPlay'), value='swiftplay'),
    #         Choice(name=_T('Deathmatch'), value='deathmatch'),
    #         Choice(name=_T('Spike Rush'), value='spikerush'),
    #         Choice(name=_T('Escalation'), value='ggteam'),
    #         Choice(name=_T('Replication'), value='onefa'),
    #         Choice(name=_T('Snowball Fight'), value='snowball'),
    #         Choice(name=_T('Custom'), value='custom'),
    #     ]
    # )
    # @app_commands.describe(mode=_T('The queue to show your carrier for'))
    # @app_commands.rename(mode=_T('mode'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def carrier(self, interaction: discord.Interaction, mode: Choice[str] | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('match'), description=_T('Shows latest match details'))
    # @app_commands.choices(
    #     mode=[
    #         Choice(name=_T('Unrated'), value='unrated'),
    #         Choice(name=_T('Competitive'), value='competitive'),
    #         # Choice(name=_T('SwiftPlay'), value='swiftplay'),
    #         Choice(name=_T('Deathmatch'), value='deathmatch'),
    #         Choice(name=_T('Spike Rush'), value='spikerush'),
    #         Choice(name=_T('Escalation'), value='ggteam'),
    #         Choice(name=_T('Replication'), value='onefa'),
    #         Choice(name=_T('Snowball Fight'), value='snowball'),
    #         Choice(name=_T('Custom'), value='custom'),
    #     ]
    # )
    # @app_commands.describe(mode=_T('The queue to show your latest match for'))
    # @app_commands.rename(mode=_T('mode'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def match(self, interaction: discord.Interaction, mode: Choice[str] | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('patchnote'), description=_T('Patch notes'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def patchnote(self, interaction: discord.Interaction) -> None:
    #     ...

    # # infomation commands

    # @app_commands.command(name=_T('agent'), description=_T('View agent info'))
    # @app_commands.guild_only()
    # @app_commands.rename(agent='agent')
    # # @dynamic_cooldown(cooldown_5s)
    # async def agent(self, interaction: discord.Interaction, agent: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('buddy'), description=_T('View buddy info'))
    # @app_commands.guild_only()
    # @app_commands.rename(buddy='buddy')
    # # @dynamic_cooldown(cooldown_5s)
    # async def buddy(self, interaction: discord.Interaction, buddy: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('bundle'), description='inspect a specific bundle')
    # @app_commands.describe(bundle="The name of the bundle you want to inspect!")
    # @app_commands.rename(bundle=_T('bundle'))
    # @app_commands.guild_only()
    # # @dynamic_cooldown(cooldown_5s)
    # async def bundle(self, interaction: discord.Interaction, bundle: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('spray'), description=_T('View spray info'))
    # @app_commands.guild_only()
    # @app_commands.rename(spray='spray')
    # # @dynamic_cooldown(cooldown_5s)
    # async def spray(self, interaction: discord.Interaction, spray: str | None = None) -> None:
    #     ...

    # player = app_commands.Group(name=_T('player'), description=_T('Player commands'), guild_only=True)

    # @player.command(name=_T('card'), description=_T('View player card'))
    # @app_commands.rename(card='card')
    # # @dynamic_cooldown(cooldown_5s)
    # async def player_card(self, interaction: discord.Interaction, card: str | None = None) -> None:
    #     ...

    # @player.command(name=_T('title'), description=_T('View player title'))
    # @app_commands.rename(title='title')
    # # @dynamic_cooldown(cooldown_5s)
    # async def player_title(self, interaction: discord.Interaction) -> None:
    #     ...

    # @app_commands.command(name=_T('weapon'), description=_T('View weapon info'))
    # @app_commands.guild_only()
    # @app_commands.rename(weapon='weapon')
    # # @dynamic_cooldown(cooldown_5s)
    # async def weapon(self, interaction: discord.Interaction, weapon: str | None = None) -> None:
    #     ...

    # @app_commands.command(name=_T('skin'), description=_T('View skin info'))
    # @app_commands.guild_only()
    # @app_commands.rename(skin='skin')
    # # @dynamic_cooldown(cooldown_5s)
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
    # @dynamic_cooldown(cooldown_5s)
    # @app_commands.guild_only()
    # async def stats(self, interaction: Interaction, queue: Choice[str] = "null") -> None:
    #     await interaction.response.defer()

    # @app_commands.describe(queue=_T('Party commands'))
    # @dynamic_cooldown(cooldown_5s)
    # @app_commands.guild_only()
    # async def party(self, interaction: Interaction) -> None:
    #     await interaction.response.defer()

    # party = app_commands.Group(name=_T('party'), description=_T('Party commands'), guild_only=True)
    #
    # @party.command(name=_T('invite'), description=_T('Invite a player to your party'))
    # @dynamic_cooldown(cooldown_5s)
    # async def party_invite(self, interaction: Interaction, player: discord.User) -> None:
    #     ...
    #
    # @party.command(name=_T('invite_by_name'), description=_T('Invite a player to your party by name'))
    # @dynamic_cooldown(cooldown_5s)
    # async def party_invite_by_name(self, interaction: Interaction, player: str) -> None:
    #     ...
    #
    # @party.command(name=_T('kick'), description=_T('Kick a player from your party'))
    # @dynamic_cooldown(cooldown_5s)
    # async def party_kick(self, interaction: Interaction, player: discord.User) -> None:
    #     ...
    #
    # @party.command(name=_T('leave'), description=_T('Leave your party'))
    # @dynamic_cooldown(cooldown_5s)
    # async def party_leave(self, interaction: Interaction) -> None:
    #     ...

    #
    # @app_commands.command(name=_T('profile'), description=_T('Shows your profile'))
    # @app_commands.guild_only()
    # async def profile(self, interaction: Interaction) -> None:
    #
    #     await interaction.response.defer()
    #
    #     riot_acc = await self.get_riot_account(user_id=interaction.user.id)
    #     client = await self.v_client.run(auth=riot_acc)
    #
    #     loadout = await client.fetch_player_loadout()
    #
    #     file = await profile_card(loadout)
    #
    #     embed = Embed(colour=0x63C0B5)
    #     embed.set_image(url="attachment://profile.png")
    #
    #     await interaction.followup.send(embed=embed, file=file)
