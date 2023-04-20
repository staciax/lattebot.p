from __future__ import annotations

import contextlib
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import discord
import valorantx2 as valorantx
from async_lru import alru_cache
from discord import ui

from core.ui.views import ViewAuthor

from . import embeds as e

if TYPE_CHECKING:
    from valorantx2 import RiotAuth

    import core.utils.chat_formatting as chat
    from core.bot import LatteMaid

    from ..valorantx2_custom import Client as ValorantClient
    from .embeds import Embed


class FeaturedBundleButton(ui.Button['FeaturedBundleView']):
    def __init__(self, other_view: FeaturedBundleView, **kwargs: Any) -> None:
        self.other_view = other_view
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.other_view is not None
        self.other_view.selected = True
        # TODO: all_embeds get embeds
        # await interaction.response.edit_message(embeds=self.other_view.all_embeds[self.custom_id], view=None)


class FeaturedBundleView(ViewAuthor):
    def __init__(
        self, interaction: discord.Interaction[LatteMaid], bundles: List[valorantx.FeaturedBundle | None]
    ) -> None:
        self.interaction = interaction
        self.bundles = bundles
        # self.v_locale = ValorantLocale.from_discord(str(interaction.locale))
        # self.all_embeds: Dict[str, List[discord.Embed]] = {}
        super().__init__(interaction, timeout=600)
        self.selected: bool = False
        self.banner_embed: Optional[Embed] = None
        self.item_embeds: Optional[List[Embed]] = None

    def build_buttons(self, bundles: List[valorantx.FeaturedBundle]) -> None:
        for index, bundle in enumerate(bundles, start=1):
            self.add_item(
                FeaturedBundleButton(
                    other_view=self,
                    label=str(index) + '. ' + bundle.display_name_localized(),
                    custom_id=bundle.uuid,
                    style=discord.ButtonStyle.blurple,
                )
            )

    async def on_timeout(self) -> None:
        if not self.selected:
            original_response = await self.interaction.original_response()
            if original_response:
                for item in self.children:
                    if isinstance(item, ui.Button):
                        item.disabled = True
                await original_response.edit(view=self)

    async def start(self) -> None:
        if len(self.bundles) > 1:
            # self.build_buttons(bundles)
            embeds = e.select_featured_bundles_e(self.bundles, locale=valorantx.Locale.english)
            # for embed in embeds:
            #     if embed.custom_id is not None and embed.thumbnail.url is not None:
            #         color_thief = await self.bot.get_or_fetch_colors(embed.custom_id, embed.thumbnail.url)
            #         embed.colour = random.choice(color_thief)
            await self.interaction.followup.send(embeds=embeds, view=self)
            return
        elif len(self.bundles) == 1:
            bundle = self.bundles[0]
            if bundle is not None:
                b = e.BundleEmbed(bundle, locale=valorantx.Locale.english)
                self.banner_embed = embed_banner = b.banner_embed()
                self.item_embeds = embed_items = b.item_embeds()
                embeds = [embed_banner, *embed_items]
                # TODO: make bundle view if embed_i more than 10
                await self.interaction.followup.send(embeds=embeds[:10])
                return

        if None in self.bundles:
            self.bot.dispatch('bundle_not_found')

        await self.interaction.followup.send("No featured bundles found")


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

    async def stop(self) -> None:
        self.bot.loop.create_task(self.fetch.cache_close())
        return super().stop()

    async def send(self, **kwargs: Any) -> None:
        if self.message is None:
            self.message = await self.interaction.followup.send(**kwargs, view=self)
            return
        else:
            await self.safe_edit_message(self.message, **kwargs, view=self)

    # @alru_cache(maxsize=5)
    async def fetch(self, riot_auth: RiotAuth) -> Any:
        raise NotImplementedError

    async def start(self, **kwargs: Any) -> None:
        pass


class StoreSwitchView(SwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], client: ValorantClient) -> None:
        super().__init__(interaction, client, user=None, row=0)

    # @alru_cache(maxsize=5)
    async def fetch(self, riot_auth: RiotAuth) -> valorantx.StoreFront:
        sf = await self.v_client.fetch_store_front()
        return sf

    # @alru_cache(maxsize=32, ttl=60 * 60)
    # async def get_embeds(self, riot_auth: RiotAuth, locale: Optional[valorantx.Locale]) -> List[discord.Embed]:
    #     sf = await self.v_client.fetch_store_front(riot_auth)
    #     return store_e(sf.get_store(), riot_auth, locale=locale)

    async def start(self) -> None:
        sf = await self.fetch(self.v_client.http._riot_auth)
        embeds = e.store_e(
            sf.skins_panel_layout, riot_auth=self.v_client.http._riot_auth, locale=valorantx.Locale.english
        )
        await self.interaction.followup.send(embeds=embeds, view=self)
        # await self.send(embeds=embeds)

    # async def on_timeout(self) -> None:
    #     self.get_embeds.cache_clear()
    #     return await super().on_timeout()


class NightMarketSwitchView(SwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], client: ValorantClient) -> None:
        super().__init__(interaction, client, user=None, row=0)

    # @alru_cache(maxsize=5)
    async def fetch(self, riot_auth: RiotAuth) -> valorantx.StoreFront:
        sf = await self.v_client.fetch_store_front()
        return sf

    async def start(self) -> None:
        sf = await self.fetch(self.v_client.http._riot_auth)
        if sf.bonus_store is None:
            raise Exception(f"{chat.bold('Nightmarket')} is not available.")
        embeds = e.nightmarket_e(sf.bonus_store, self.v_client.http._riot_auth, locale=valorantx.Locale.english)
        await self.send(embeds=embeds)


class WalletSwitchView(SwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], client: ValorantClient) -> None:
        super().__init__(interaction, client, user=None, row=0)

    # @alru_cache(maxsize=5)
    async def fetch(self, riot_auth: RiotAuth) -> valorantx.Wallet:
        wallet = await self.v_client.fetch_wallet()
        return wallet

    async def start(self) -> None:
        wallet = await self.fetch(self.v_client.http._riot_auth)
        embed = e.wallet_e(wallet, self.v_client.http._riot_auth, locale=valorantx.Locale.english)
        await self.send(embed=embed)
