from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, List

import discord

# from async_lru import alru_cache
import valorantx2 as valorantx
from discord import ui

from core.ui.views import ViewAuthor

from . import embeds as e

if TYPE_CHECKING:
    from valorantx2 import RiotAuth

    from core.bot import LatteMaid

    from ..valorantx2_custom import Client as ValorantClient


class ButtonAccountSwitchX(ui.Button['SwitchView']):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(style=discord.ButtonStyle.gray, **kwargs)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None

        # self.view.bot.translator.set_locale(interaction.locale)
        # self.view.locale = interaction.locale
        # await interaction.response.defer()

        # # enable all buttons without self
        # self.disabled = True
        # for item in self.view.children:
        #     if isinstance(item, ui.Button):
        #         if item.custom_id != self.custom_id:
        #             item.disabled = False

        # for riot_auth in self.view.riot_auth_list:
        #     if riot_auth.puuid == self.custom_id:
        #         await self.view.start_view(riot_auth)
        #         break


class SwitchView(ViewAuthor):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        client: ValorantClient,
        user: Any = None,
        row: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(interaction, timeout=kwargs.get('timeout', 60.0 * 15), **kwargs)
        self.v_client: ValorantClient = client
        self.user: Any = user
        self._build_buttons(row)
        # self.v_locale = self.bot.valorant.v_locale(interaction.locale)

    def _build_buttons(self, row: int = 0) -> None:
        for index, acc in enumerate([], start=1):
            if index >= 4:
                row += 1
            # self.add_item(
            #     ButtonAccountSwitchX(
            #         label="Account #" + str(index) if acc.hide_display_name else acc.display_name,
            #         custom_id=acc.puuid,
            #         disabled=(index == 1),
            #         row=row,
            #     )
            # )

    def remove_switch_button(self) -> None:
        for child in self.children:
            if isinstance(child, ButtonAccountSwitchX):
                self.remove_item(child)

    async def interaction_check(self, interaction: discord.Interaction[LatteMaid], /) -> bool:
        if await super().interaction_check(interaction):
            # self.v_locale = self.bot.valorant.v_locale(interaction.locale)
            return True
        return False

    @staticmethod
    async def safe_edit_message(
        message: discord.Message | discord.InteractionMessage, **kwargs: Any
    ) -> discord.Message | discord.InteractionMessage | None:
        with contextlib.suppress(discord.errors.HTTPException, discord.errors.Forbidden):
            return await message.edit(**kwargs)

    async def on_timeout(self) -> None:
        self.disable_buttons()
        if self.message is None:
            try:
                response = await self.interaction.original_response()
            except (discord.errors.HTTPException, discord.errors.ClientException, discord.errors.NotFound):
                return
            else:
                await self.safe_edit_message(response, view=self)
        else:
            await self.safe_edit_message(self.message, view=self)

    async def start(self, **kwargs: Any) -> None:
        pass

    async def send(self, **kwargs: Any) -> None:
        if self.message is None:
            self.message = await self.interaction.followup.send(**kwargs, view=self)
            return
        else:
            await self.safe_edit_message(self.message, **kwargs, view=self)


class StoreSwitchView(SwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], client: ValorantClient) -> None:
        super().__init__(interaction, client, user=None, row=0)

    async def build_embeds(
        self, riot_auth: RiotAuth, locale: valorantx.Locale = valorantx.Locale.english
    ) -> List[discord.Embed]:
        sf = await self.v_client.fetch_store_front()
        embeds = e.store_e(sf.skins_panel_layout, riot_auth=self.v_client.http._riot_auth, locale=locale)
        return embeds

    # @alru_cache(maxsize=32, ttl=60 * 60)
    # async def get_embeds(self, riot_auth: RiotAuth, locale: Optional[valorantx.Locale]) -> List[discord.Embed]:
    #     sf = await self.v_client.fetch_store_front(riot_auth)
    #     return store_e(sf.get_store(), riot_auth, locale=locale)

    async def start(self) -> None:
        embeds = await self.build_embeds(self.v_client.http._riot_auth)
        await self.interaction.followup.send(embeds=embeds, view=self)
        # await self.send(embeds=embeds)

    # async def on_timeout(self) -> None:
    #     self.get_embeds.cache_clear()
    #     return await super().on_timeout()
