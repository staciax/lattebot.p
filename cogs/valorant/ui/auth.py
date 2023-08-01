from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
from discord import ButtonStyle, ui

from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from core.ui.modal import Modal
from core.ui.views import ViewAuthor
from valorantx2.errors import RiotMultifactorError

from ..account_manager import AccountManager
from ..auth import RiotAuth
from ..error import (  # ErrorHandler,; RiotAuthMaxLimitReached,; RiotAuthNotLinked,
    RiotAuthAlreadyLinked,
    RiotAuthMultiFactorTimeout,
)

if TYPE_CHECKING:
    from typing_extensions import Self

    from core.bot import LatteMaid


_log = logging.getLogger(__name__)

_ = I18n('valorant.ui.auth', Path(__file__).resolve().parent, read_only=True)

RIOT_PASSWORD_REGEX = re.compile(r'^.{8,128}$')
RIOT_USERNAME_REGEX = re.compile(r'^.{4,24}$')


class ManageView(ViewAuthor):
    account_manager: AccountManager

    def __init__(self, interaction: discord.Interaction[LatteMaid], timeout: float = 180.0) -> None:
        super().__init__(interaction, timeout=timeout)

    async def _init(self) -> None:
        user = await self.bot.db.fetch_user(self.author.id)
        if user is None:
            raise RuntimeError('User not found')
        self.account_manager = AccountManager(user, self.bot, re_authorize=False)
        await self.account_manager.wait_until_ready()

    async def start(self) -> None:
        await self._init()
        self.fill_itmes()
        embed = self.front_embed()
        await self.interaction.response.send_message(embed=embed, view=self)
        self.message = await self.interaction.original_response()

    async def refresh(self) -> None:
        user = await self.bot.db.fetch_user(self.author.id)
        if user is None:
            raise RuntimeError('User not found')
        self.account_manager = AccountManager(user, self.bot, re_authorize=False)
        await self.account_manager.wait_until_ready()
        embed = self.front_embed()
        assert self.message is not None
        await self.message.edit(embed=embed, view=self)

    def fill_itmes(self) -> None:
        self.clear_items()
        self.add_items(
            AddAccountView(locale=self.locale),
            RemoveAccountView(locale=self.locale),
            AccountSelect(locale=self.locale).add_options(self.account_manager.accounts),
        )

    def front_embed(self) -> Embed:
        embed = Embed(description=_('- You don\'t have any accounts yet', self.locale)).white()
        embed.set_author(name=_('account.manager', self.locale), icon_url=self.author.display_avatar)

        if len(self.account_manager.accounts) > 0:
            embed.description = ''
            for account in self.account_manager.accounts:
                embed.description += f'- {account.region} - {account.riot_id}\n'

        return embed


class RiotMultiFactorModal(Modal):
    """Modal for riot login with multifactorial authentication"""

    def __init__(self, try_auth: RiotAuth, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__(
            interaction=interaction,
            title=_('Two-factor authentication'),
            timeout=180.0,
            custom_id=f'wait_for_modal_{try_auth.puuid}',
        )
        self.try_auth: RiotAuth = try_auth
        self.code: str | None = None
        self.interaction: discord.Interaction[LatteMaid] | None = None
        self.two2fa = ui.TextInput(
            label=_('Input 2FA Code', self.locale),
            max_length=6,
            # min_length=6,
            style=discord.TextStyle.short,
            # custom_id=self.custom_id + '_2fa' + try_auth.puuid,  # TODO: + puuid
            placeholder=(
                _('You have 2FA enabled!')
                if self.try_auth.multi_factor_email is None
                else _('Riot sent a code to ') + self.try_auth.multi_factor_email
            ),
        )
        self.add_item(self.two2fa)

    async def on_submit(self, interaction: discord.Interaction[LatteMaid]) -> None:
        code = self.two2fa.value

        if not code:
            await interaction.response.send_message(_('Please input 2FA code'), ephemeral=True)
            return

        if not code.isdigit():
            await interaction.response.send_message(_('Invalid code'), ephemeral=True)
            return

        self.code = code
        self.interaction = interaction
        self.stop()


class UsernamePasswordModal(Modal):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        title: str,
        custom_id: str,
        *,
        timeout: float | None = None,
    ) -> None:
        super().__init__(interaction, title=title, custom_id=custom_id, timeout=timeout)
        self.interaction: discord.Interaction[LatteMaid] | None = None
        self.username = ui.TextInput(
            label=_('Username', self.locale),
            max_length=24,
            min_length=1,
            style=discord.TextStyle.short,
            placeholder=_('username'),
        )
        self.password = ui.TextInput(
            label=_('Password', self.locale),
            max_length=128,
            min_length=1,
            style=discord.TextStyle.short,
            placeholder=_('password'),
        )
        self.add_item(self.username)
        self.add_item(self.password)

    async def on_submit(self, interaction: discord.Interaction[LatteMaid]) -> None:
        if not self.username.value:
            await interaction.response.send_message(_('Please input username'), ephemeral=True)
            return

        if len(self.username.value) < 4:
            await interaction.response.send_message(_('Username must be at least 4 characters'), ephemeral=True)

        if not self.password.value:
            await interaction.response.send_message(_('Please input password'), ephemeral=True)
            return

        if len(self.password.value) < 8:
            await interaction.response.send_message(_('Password must be at least 8 characters'), ephemeral=True)
            return

        self.interaction = interaction
        self.stop()


class RitoAuthUsernamePasswordButton(ui.Button['ManageView']):
    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None

        login_modal = UsernamePasswordModal(
            interaction,
            title=_('login', interaction.locale),
            custom_id='modal_riot_auth_login',
        )
        await interaction.response.send_modal(login_modal)
        await login_modal.wait()
        assert login_modal.interaction is not None
        await login_modal.interaction.response.defer(ephemeral=True, thinking=True)

        riot_auth = RiotAuth()

        try:
            await riot_auth.authorize(login_modal.username.value.strip(), login_modal.password.value.strip(), remember=True)
        except RiotMultifactorError:
            embed = Embed(title=_('Two-factor authentication'), description=_('You have 2FA enabled!')).blurple()
            multi_view = MultiFactorView(interaction, riot_auth)
            message_2fa = await login_modal.interaction.followup.send(
                embed=embed, ephemeral=True, view=multi_view, wait=True
            )
            await multi_view.wait()
            await message_2fa.delete()
            if multi_view.code is None:
                raise RiotAuthMultiFactorTimeout('You did not enter the code in time.')

            await riot_auth.authorize_multi_factor(multi_view.code, remember=True)

        # check if already linked
        riot_account = await self.view.bot.db.fetch_riot_account_by_puuid_and_owner_id(
            puuid=riot_auth.puuid, owner_id=interaction.user.id
        )
        if riot_account is not None:
            await self.view.bot.db.update_riot_account(
                puuid=riot_auth.puuid,
                owner_id=interaction.user.id,
                game_name=riot_auth.game_name,
                tag_line=riot_auth.tag_line,
                region=riot_auth.region or riot_account.region,
                token_type=riot_auth.token_type,
                expires_at=riot_auth.expires_at,
                id_token=riot_auth.id_token,
                access_token=riot_auth.access_token,
                entitlements_token=riot_auth.entitlements_token,
                ssid=riot_auth.get_ssid(),
            )
            raise RiotAuthAlreadyLinked('You already have this account linked.')

        # fetch userinfo and region
        try:
            await riot_auth.fetch_userinfo()
        except aiohttp.ClientResponseError as e:
            _log.error('riot auth error fetching userinfo', exc_info=e)

        # # set region if specified
        # if region is not None:
        #     riot_auth.region = region.value
        # else:
        # fetch region if not specified
        try:
            await riot_auth.fetch_region()
        except aiohttp.ClientResponseError as e:
            riot_auth.region = 'ap'  # default to ap
            _log.error('riot auth error fetching region', exc_info=e)
        assert riot_auth.region is not None

        embed = Embed().blurple()
        embed.add_field(name='Riot ID', value=riot_auth.riot_id, inline=False)
        embed.add_field(name='Region', value=riot_auth.region, inline=False)
        embed.set_footer(text='ID: ' + riot_auth.puuid)

        view = ConfirmView(interaction)
        message = await login_modal.interaction.followup.send(embed=embed, ephemeral=True, view=view, wait=True)
        await view.wait()

        if not view.value:
            await interaction.followup.send(_('You did not confirm the login.'), ephemeral=True)
            return

        await message.delete()

        riot_account = await self.view.bot.db.add_riot_account(
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

        if not len(self.view.account_manager.accounts):
            ...
            # set main account

        user = await self.view.bot.db.fetch_user(interaction.user.id)
        if user is None:
            raise RuntimeError('User not found')

        await self.view.refresh()


class MultiFactorView(ViewAuthor):
    def __init__(self, interaction: discord.Interaction[LatteMaid], riot_auth: RiotAuth) -> None:
        super().__init__(interaction, timeout=180.0)
        self.riot_auth = riot_auth
        self.code: str | None = None

    @ui.button(label='Enter 2FA Code', style=discord.ButtonStyle.primary)
    async def enter_2fa_code(self, interaction: discord.Interaction[LatteMaid], button: discord.ui.Button) -> None:
        multi_modal = RiotMultiFactorModal(self.riot_auth, interaction)
        await interaction.response.send_modal(multi_modal)
        await multi_modal.wait()

        assert multi_modal.interaction is not None
        await multi_modal.interaction.response.defer(ephemeral=True)

        if multi_modal.code is None:
            raise RiotAuthMultiFactorTimeout('You did not enter the code in time.')

        self.code = multi_modal.code

        self.stop()


class Enter2FACodeButton(ui.Button['ManageView']):
    def __init__(
        self,
        label: str | None = None,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.primary,
        disabled: bool = False,
        emoji: str | discord.Emoji | discord.PartialEmoji | None = None,
    ):
        super().__init__(style=style, label=label, disabled=disabled, emoji=emoji)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> Any:
        return await super().callback(interaction)


class ConfirmView(ViewAuthor):
    def __init__(self, interaction: discord.Interaction[LatteMaid], timeout: float = 180.0) -> None:
        super().__init__(interaction, timeout=timeout)
        self.value: bool | None = None
        self.region: str | None = None
        self.add_item(RegionSelect(locale=self.locale))

    @ui.button(label='Confirm', style=discord.ButtonStyle.green, row=1)
    async def confirm(self, interaction: discord.Interaction[LatteMaid], button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @ui.button(label='Cancel', style=discord.ButtonStyle.red, row=1)
    async def cancel(self, interaction: discord.Interaction[LatteMaid], button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()


class RegionSelect(ui.Select):
    def __init__(self, *, locale: discord.Locale) -> None:
        super().__init__(placeholder=_('select.region', locale), row=0)
        self.locale = locale
        self.add_options()

    def add_options(self) -> Self:
        self.add_option(label='Asia Pacific', value='ap', emoji='🌏')
        self.add_option(label='Europe', value='eu', emoji='🇪🇺')
        self.add_option(label='North America / Latin America / Brazil', value='na', emoji='🇺🇸')
        self.add_option(label='Korea', value='kr', emoji='🇰🇷')
        # self.add_option(label='Public Beta Environment', value='pbe', emoji='🔧')
        return self

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        value = self.values[0]
        self.view.region = value
        await interaction.response.defer()


class PreviousButton(ui.Button['ManageView']):
    def __init__(self, row: int = 1, **kwargs: Any) -> None:
        super().__init__(label='<', row=row, **kwargs)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None

        self.view.clear_items()
        self.view.fill_itmes()
        embed = self.view.front_embed()

        await interaction.response.edit_message(embed=embed, view=self.view)


class AddAccountView(ui.Button['ManageView']):
    def __init__(self, *, locale: discord.Locale = discord.Locale.american_english) -> None:
        super().__init__(
            label=_('button.add.account', locale),
            style=ButtonStyle.blurple,
        )
        self.locale = locale

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None

        if len(self.view.account_manager.accounts) >= 10:
            ...
            # raise RiotAuthMaxLimitReached('You can only link up to 10 accounts.')

        self.view.clear_items()
        self.view.add_items(RitoAuthUsernamePasswordButton(label='login'), PreviousButton())

        embed = Embed().white()
        embed.set_author(name=_('add.an.account', self.locale), icon_url=interaction.user.display_avatar)
        # latte bot privacy policy and terms of service
        embed.description = _(
            '- Before you start, please read our [Privacy Policy](https://latte.gg/privacy) and [Terms of Service](https://latte.gg/terms).',
            interaction.locale,
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class RemoveAccountView(ui.Button['ManageView']):
    def __init__(self, *, locale: discord.Locale = discord.Locale.american_english) -> None:
        super().__init__(
            label=_('button.remove.account', locale),
            style=ButtonStyle.red,
        )
        self.locale = locale

    async def callback(self, interaction: discord.Interaction[LatteMaid]):
        assert self.view is not None
        await self.view.bot.db.remove_riot_accounts(interaction.user.id)


class AccountSelect(ui.Select['ManageView']):
    def __init__(
        self,
        *,
        locale: discord.Locale,
    ) -> None:
        super().__init__(placeholder=_('select.main.account', locale))
        self.locale = locale

    def add_options(self, riot_account: list[RiotAuth]) -> Self:
        if not riot_account:
            self.add_option(label='-', value='-')
            self.disabled = True

        # ☆
        for account in riot_account:
            label = str(account.riot_id)
            if account.display_name is not None:
                label += f' ({account.display_name[:70]})'
            self.add_option(
                label=label,
                value=str(account.id) + ':' + account.puuid,
                # emoji=
            )
        return self

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        value = self.values[0]
        row_id, puuid = value.split(':')
