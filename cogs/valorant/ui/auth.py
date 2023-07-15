from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord import ui
from discord.enums import ButtonStyle
from discord.utils import MISSING

from core.bot import LatteMaid
from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from core.ui.modal import Modal
from core.ui.views import ViewAuthor

from ..account_manager import AccountManager
from ..error import (
    ErrorHandler,
    RiotAuthAlreadyLinked,
    RiotAuthMaxLimitReached,
    RiotAuthMultiFactorTimeout,
    RiotAuthNotLinked,
)

if TYPE_CHECKING:
    from typing_extensions import Self

    from core.bot import LatteMaid

    from ..auth import RiotAuth


_ = I18n('valorant.ui.auth', Path(__file__).resolve().parent, read_only=True)


# username: app_commands.Range[str, 1, 24],
# password: app_commands.Range[str, 1, 128],
# region: app_commands.Choice[str] | None

# riot_auth = RiotAuth()

# try:
#     await riot_auth.authorize(username.strip(), password.strip(), remember=True)
# except RiotMultifactorError:
#     multi_modal = RiotMultiFactorModal(riot_auth, interaction)
#     await interaction.response.send_modal(multi_modal)
#     await multi_modal.wait()

#     if multi_modal.code is None:
#         raise RiotAuthMultiFactorTimeout('You did not enter the code in time.')

#     interaction = multi_modal.interaction or interaction

#     if multi_modal.interaction is not None:
#         await interaction.response.defer(ephemeral=True, thinking=True)

#     try:
#         await riot_auth.authorize_multi_factor(multi_modal.code, remember=True)
#     except Exception as e:
#         await multi_modal.on_error(interaction, e)
#         return
#     finally:
#         multi_modal.stop()

# else:
#     await interaction.response.defer(ephemeral=True)

# # check if already linked
# riot_account = await self.bot.db.get_riot_account_by_puuid_and_owner_id(
#     puuid=riot_auth.puuid, owner_id=interaction.user.id
# )
# if riot_account is not None:
#     raise RiotAuthAlreadyLinked('You already have this account linked.')

# # fetch userinfo and region
# try:
#     await riot_auth.fetch_userinfo()
# except aiohttp.ClientResponseError as e:
#     _log.error('riot auth error fetching userinfo', exc_info=e)

# # set region if specified
# if region is not None:
#     riot_auth.region = region.value
# else:
#     # fetch region if not specified
#     try:
#         await riot_auth.fetch_region()
#     except aiohttp.ClientResponseError as e:
#         riot_auth.region = 'ap'  # default to ap
#         _log.error('riot auth error fetching region', exc_info=e)
# assert riot_auth.region is not None

# embed = Embed().blurple()
# embed.add_field(name='Riot ID', value=riot_auth.riot_id, inline=False)
# embed.add_field(name='Region', value=riot_auth.region, inline=False)
# embed.set_footer(text='ID: ' + riot_auth.puuid)

# view = RiotAuthConfirmView(interaction)
# message = await interaction.followup.send(
#     embed=embed,
#     ephemeral=True,
#     view=view,
#     wait=True,
# )
# await view.wait()

# if not view.value:
#     raise BadArgument(_('You did not confirm the login.', interaction.locale))

# riot_account = await self.bot.db.create_riot_account(
#     interaction.user.id,
#     puuid=riot_auth.puuid,
#     game_name=riot_auth.game_name,
#     tag_line=riot_auth.tag_line,
#     region=riot_auth.region,
#     scope=riot_auth.scope,  # type: ignore
#     token_type=riot_auth.token_type,  # type: ignore
#     expires_at=riot_auth.expires_at,
#     id_token=riot_auth.id_token,  # type: ignore
#     access_token=riot_auth.access_token,  # type: ignore
#     entitlements_token=riot_auth.entitlements_token,  # type: ignore
#     ssid=riot_auth.get_ssid(),
#     notify=False,
# )
# if not len(user.riot_accounts):
#     await self.bot.db.update_user(user.id, main_account_id=riot_account.id)

# _log.info(
#     f'{interaction.user}({interaction.user.id}) linked {riot_auth.riot_id}({riot_auth.puuid}) - {riot_auth.region}'
# )
# # invalidate cache
# # self.??.invalidate(self, id=interaction.user.id)

# e = Embed(description=f'Successfully logged in {chat.bold(riot_auth.riot_id)}')
# await message.edit(embed=e, view=None)


RIOT_PASSWORD_REGEX = re.compile(r'^.{8,128}$')
RIOT_USERNAME_REGEX = re.compile(r'^.{4,24}$')


def validate_riot_password(password: str) -> bool:
    return bool(re.match(RIOT_PASSWORD_REGEX, password))


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


class RiotAuthModalLogin(Modal):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        *,
        title: str = ...,
        timeout: float | None = None,
        custom_id: str = ...,
    ) -> None:
        super().__init__(interaction, title=title, timeout=timeout, custom_id=custom_id)
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


class RiotAuthManageView(ViewAuthor):
    account_manager: AccountManager

    def __init__(self, interaction: discord.Interaction[LatteMaid], timeout: float = 180.0) -> None:
        super().__init__(interaction, timeout=timeout)

    async def _init(self) -> None:
        user = await self.bot.db.get_user(self.author.id)
        if user is None:
            raise RuntimeError('User not found')
        self.account_manager = AccountManager(user, self.bot, re_authorize=False)
        await self.account_manager.wait_until_ready()

    async def start(self) -> None:
        await self._init()
        self.add_components()
        embed = self.front_embed()
        await self.interaction.response.send_message(embed=embed, view=self)
        self.message = await self.interaction.original_response()

    def add_components(self) -> None:
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


class AddAccountView(ui.Button['RiotAuthManageView']):
    def __init__(self, *, locale: discord.Locale = discord.Locale.american_english) -> None:
        super().__init__(
            label=_('button.riot_auth.add.account', locale),
            style=ButtonStyle.blurple,
        )
        self.locale = locale

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        if len(self.view.account_manager.accounts) >= 10:
            ...
            # raise RiotAuthMaxLimitReached('You can only link up to 10 accounts.')


class RemoveAccountView(ui.Button['RiotAuthManageView']):
    def __init__(self, *, locale: discord.Locale = discord.Locale.american_english) -> None:
        super().__init__(
            label=_('button.riot_auth.remove.account', locale),
            style=ButtonStyle.red,
        )
        self.locale = locale

    async def callback(self, interaction: discord.Interaction[LatteMaid]):
        assert self.view is not None


class AccountSelect(ui.Select['RiotAuthManageView']):
    def __init__(
        self,
        *,
        locale: discord.Locale,
    ) -> None:
        super().__init__(placeholder=_('select.riot_auth.main.account', locale))
        self.locale = locale

    def add_options(self, riot_account: list[RiotAuth]) -> Self:
        if not riot_account:
            self.add_option(label='-', value='-')
            self.disabled = True

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


class RiotAuthConfirmView(ViewAuthor):
    def __init__(self, interaction: discord.Interaction[LatteMaid], timeout: float = 180.0) -> None:
        super().__init__(interaction, timeout=timeout)
        self.value: bool | None = None

    @ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction[LatteMaid], button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction[LatteMaid], button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()
