from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord import ui
from discord.enums import ButtonStyle

from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from core.ui.modal import Modal
from core.ui.views import ViewAuthor

from ..account_manager import RiotAccountManager

if TYPE_CHECKING:
    from core.bot import LatteMaid

    from ..auth import RiotAuth


_ = I18n('valorant.ui.auth', Path(__file__).resolve().parent, read_only=True)


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


class RiotAuthManageView(ViewAuthor):
    account_manager: RiotAccountManager

    def __init__(self, interaction: discord.Interaction[LatteMaid], timeout: float = 180.0) -> None:
        super().__init__(interaction, timeout=timeout)

    async def _init(self) -> None:
        user = await self.bot.db.get_user(self.author.id)
        if user is None:
            raise RuntimeError('User not found')
        self.account_manager = RiotAccountManager(user, self.bot)

    async def start(self) -> None:
        await self._init()
        self.add_components()
        embed = self.front_embed()
        await self.interaction.response.send_message(embed=embed, view=self)
        self.message = await self.interaction.original_response()

    def add_components(self) -> None:
        self.clear_items()
        self.add_items(
            AddAccountView(_('button.riot_auth.add.account', self.locale)),
            RemoveAccountView(_('button.riot_auth.remove.account', self.locale)),
            AccountSelect(_('select.riot_auth.main.account', self.locale), self.account_manager.accounts),
        )

    def front_embed(self) -> Embed:
        embed = Embed(description=_('You don\'t have any accounts yet', self.locale)).blurple()
        embed.set_author(name='Account Manager', icon_url=self.author.display_avatar)

        if len(self.account_manager.accounts) > 0:
            embed.description = ''
            for account in self.account_manager.accounts:
                embed.description += f'- {account.region} - {account.riot_id}\n'

        return embed


class AddAccountView(ui.Button['RiotAuthManageView']):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction[LatteMaid]):
        ...


class RemoveAccountView(ui.Button['RiotAuthManageView']):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction[LatteMaid]):
        ...


class AccountSelect(ui.Select['RiotAuthManageView']):
    def __init__(self, placeholder: str, riot_account: list[RiotAuth]) -> None:
        super().__init__(placeholder=placeholder)
        self.add_options(riot_account)

    def add_options(self, riot_account: list[RiotAuth]) -> None:
        for account in riot_account:
            label = str(account.riot_id)
            # if account.display_name is not None:
            #     label += f' ({account.display_name[:70]})'
            self.add_option(
                label=label,
                value=str(account.id),
                # emoji=
            )

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.view is not None
        value = self.values[0]


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
