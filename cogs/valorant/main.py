from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import aiohttp
import discord
import valorantx2 as valorantx
from discord import app_commands
from discord.app_commands import locale_str as _T
from valorantx2.auth import RiotAuth
from valorantx2.errors import RiotMultifactorError

import core.utils.chat_formatting as chat

from .abc import ValorantCog

if TYPE_CHECKING:
    from core.bot import LatteMaid

_log = logging.getLogger(__name__)


class Valorant(ValorantCog):
    def __init__(self, bot: LatteMaid) -> None:
        self.bot: LatteMaid = bot
        self.v_client: valorantx.Client = valorantx.Client()

    async def run(self) -> None:
        try:
            await asyncio.wait_for(self.v_client.init(), timeout=30)
        except asyncio.TimeoutError:
            _log.error('Valorant API Client failed to initialize within 30 seconds.')
        else:
            _log.info('Valorant API Client is ready.')
            self.bot.dispatch('v_client_ready')

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
            await self.v_client.authorize(username.strip(), password.strip(), remember=True)
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
    async def logout(self, interaction: discord.Interaction, number: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)

        e = discord.Embed(description=f"Successfully logged out all accounts")
        await interaction.followup.send(embed=e, ephemeral=True)

        # # invalidate cache
        # self.fetch_user.invalidate(self, id=interaction.user.id)
