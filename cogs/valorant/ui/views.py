from __future__ import annotations

import contextlib

# import random
from typing import TYPE_CHECKING, Any, List, Optional

import discord

# from async_lru import alru_cache
from discord import ui

import core.utils.chat_formatting as chat
from core.ui.views import ViewAuthor
from core.utils.pages import LattePages, ListPageSource

from .. import valorantx3 as valorantx
from ..valorantx3.enums import Locale as ValorantLocale, RelationType
from ..valorantx3.models import FeaturedBundle, RewardValorantAPI, StoreFront, Wallet
from . import embeds as e

if TYPE_CHECKING:
    from core.bot import LatteMaid

    from ..valorantx3 import Client as ValorantClient, RiotAuth
    from .embeds import Embed

__all__ = (
    'FeaturedBundleView',
    'SwitchView',
    'StoreSwitchView',
    'NightMarketSwitchView',
    'WalletSwitchView',
)


class ViewAuthorValorantClient(ViewAuthor):
    def __init__(
        self, interaction: discord.Interaction[LatteMaid], client: ValorantClient, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(interaction, *args, **kwargs)
        self.v_client: ValorantClient = client
        self.v_locale: ValorantLocale = valorantx.utils.locale_converter(self.interaction.locale)
        # self.interaction.extras['v_client'] = self.v_locale
        # self.interaction.extras['v_locale'] = self.v_locale

    async def interaction_check(self, interaction: discord.Interaction[LatteMaid], /) -> bool:
        if await super().interaction_check(interaction):
            self.v_locale = valorantx.utils.locale_converter(self.interaction.locale)
            # interaction.extras['v_locale'] = self.v_locale
            # self.interaction.extras['v_locale'] = self.v_locale
            return True
        return False


class FeaturedBundleButton(ui.Button['FeaturedBundleView']):
    def __init__(self, other_view: FeaturedBundleView, **kwargs: Any) -> None:
        self.other_view = other_view
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
        assert self.other_view is not None
        self.other_view.selected = True
        # TODO: all_embeds get embeds
        # await interaction.response.edit_message(embeds=self.other_view.all_embeds[self.custom_id], view=None)


class FeaturedBundleView(ViewAuthorValorantClient):
    def __init__(self, interaction: discord.Interaction[LatteMaid], client: ValorantClient) -> None:
        super().__init__(interaction, client, timeout=600)
        # self.all_embeds: Dict[str, List[discord.Embed]] = {}
        self.selected: bool = False
        self.banner_embed: Optional[Embed] = None
        self.item_embeds: Optional[List[Embed]] = None

    def build_buttons(self, bundles: List[FeaturedBundle]) -> None:
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

    async def start_view(self) -> None:
        bundles = await self.v_client.fetch_featured_bundle()

        if len(bundles) > 1:
            # self.build_buttons(bundles)
            embeds = e.select_featured_bundles_e(bundles, locale=self.v_locale)
            # for embed in embeds:
            #     if embed.custom_id is not None and embed.thumbnail.url is not None:
            #         color_thief = await self.bot.get_or_fetch_colors(embed.custom_id, embed.thumbnail.url)
            #         embed.colour = random.choice(color_thief)
            await self.interaction.followup.send(embeds=embeds, view=self)
            return
        elif len(bundles) == 1:
            bundle = bundles[0]
            if bundle is not None:
                b = e.BundleEmbed(bundle, locale=self.v_locale)
                self.banner_embed = embed_banner = b.banner_embed()
                self.item_embeds = embed_items = b.item_embeds()
                embeds = [embed_banner, *embed_items]
                # TODO: make bundle view if embed_i more than 10
                await self.interaction.followup.send(embeds=embeds[:10])
                return

        if None in bundles:
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


class SwitchView(ViewAuthorValorantClient):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMaid],
        client: ValorantClient,
        user: Any = None,
        row: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(interaction, client, **kwargs)
        self.timeout = kwargs.pop('timeout', 60.0 * 15)
        self.user: Any = user
        self._build_buttons(row)

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

    async def start_view(self, **kwargs: Any) -> None:
        pass


class StoreSwitchView(SwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], client: ValorantClient) -> None:
        super().__init__(interaction, client, user=None, row=0)

    # @alru_cache(maxsize=5)
    async def fetch(self, riot_auth: RiotAuth) -> StoreFront:
        sf = await self.v_client.fetch_store_front()
        return sf

    # @alru_cache(maxsize=32, ttl=60 * 60)
    # async def get_embeds(self, riot_auth: RiotAuth, locale: Optional[valorantx.Locale]) -> List[discord.Embed]:
    #     sf = await self.v_client.fetch_store_front(riot_auth)
    #     return store_e(sf.get_store(), riot_auth, locale=locale)

    async def start_view(self) -> None:
        sf = await self.fetch(self.v_client.http._riot_auth)
        embeds = e.store_e(sf.skins_panel_layout, riot_auth=self.v_client.http._riot_auth, locale=self.v_locale)
        await self.interaction.followup.send(embeds=embeds, view=self)
        # await self.send(embeds=embeds)

    # async def on_timeout(self) -> None:
    #     self.get_embeds.cache_clear()
    #     return await super().on_timeout()


class NightMarketSwitchView(SwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], client: ValorantClient, hide: bool) -> None:
        super().__init__(interaction, client, user=None, row=0)
        self.hide = hide
        self.front_embed: Optional[Embed] = None
        self.prompt_embeds: Optional[List[Embed]] = None
        self.embeds: Optional[List[Embed]] = None
        self.current_opened: int = 1
        if not hide:
            self.clear_items()

    @ui.button(label="Open Once", style=discord.ButtonStyle.primary)
    async def open_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        assert self.message is not None
        if self.embeds is None:
            return
        if self.current_opened > len(self.embeds):
            return
        if self.prompt_embeds is None:
            return

        embeds = []
        embeds.extend(self.embeds[: self.current_opened])
        embeds.extend(self.prompt_embeds[self.current_opened :])
        embeds.insert(0, self.front_embed)

        if self.current_opened == len(self.embeds):
            self.clear_items()

        try:
            await self.message.edit(embeds=embeds, view=self)
        except (discord.errors.HTTPException, discord.errors.Forbidden, discord.errors.NotFound):
            pass
        else:
            self.current_opened += 1

    @ui.button(label="Open All", style=discord.ButtonStyle.primary)
    async def open_all_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        assert self.message is not None
        if self.embeds is None:
            return
        if self.current_opened > len(self.embeds):
            return
        if self.prompt_embeds is None:
            return

        embeds = [self.front_embed, *self.embeds]
        self.clear_items()

        try:
            await self.message.edit(embeds=embeds, view=self)
        except (discord.errors.HTTPException, discord.errors.Forbidden, discord.errors.NotFound):
            pass

    async def on_timeout(self) -> None:
        if self.message is None:
            return
        if self.embeds is None:
            return
        self.remove_item(self.open_button)
        self.remove_item(self.open_all_button)
        embeds = [self.front_embed, *self.embeds]
        await self.safe_edit_message(self.message, embeds=embeds, view=self)

    # @alru_cache(maxsize=5)
    async def fetch(self, riot_auth: RiotAuth) -> StoreFront:
        sf = await self.v_client.fetch_store_front()
        return sf

    async def start_view(self) -> None:
        sf = await self.fetch(self.v_client.http._riot_auth)
        if sf.bonus_store is None:
            raise Exception(f"{chat.bold('Nightmarket')} is not available.")

        self.front_embed = front_embed = e.nightmarket_front_e(
            sf.bonus_store, self.v_client.http._riot_auth, locale=self.v_locale
        )
        self.embeds = embeds = [e.skin_e(skin, locale=self.v_locale) for skin in sf.bonus_store.skins]

        if self.hide:
            self.prompt_embeds = prompt_embeds = [
                e.skin_e_hide(skin, locale=self.v_locale) for skin in sf.bonus_store.skins
            ]
            await self.send(embeds=[front_embed, *prompt_embeds])
            return

        await self.send(embeds=embeds)


class WalletSwitchView(SwitchView):
    def __init__(self, interaction: discord.Interaction[LatteMaid], client: ValorantClient) -> None:
        super().__init__(interaction, client, user=None, row=0)

    # @alru_cache(maxsize=5)
    async def fetch(self, riot_auth: RiotAuth) -> Wallet:
        wallet = await self.v_client.fetch_wallet()
        return wallet

    async def start_view(self) -> None:
        wallet = await self.fetch(self.v_client.http._riot_auth)
        embed = e.wallet_e(wallet, self.v_client.http._riot_auth, locale=self.v_locale)
        await self.send(embed=embed)


class GamePassPageSource(ListPageSource['RewardValorantAPI']):
    def __init__(self, contract: valorantx.Contract, riot_auth: RiotAuth, locale: ValorantLocale) -> None:
        self.embed = e.GamePassEmbed(contract, riot_auth, locale=locale)
        super().__init__(contract.content.get_all_rewards(), per_page=1)

    async def format_page(self, menu: GamePassView, page: Any):
        reward = self.entries[menu.current_page]
        return self.embed.build_page_embed(menu.current_page, reward, locale=menu.v_locale)


class GamePassView(SwitchView, LattePages):
    embed: e.GamePassEmbed

    def __init__(
        self, interaction: discord.Interaction[LatteMaid], client: ValorantClient, relation_type: valorantx.RelationType
    ) -> None:
        self.relation_type = relation_type
        super().__init__(interaction, client, user=None, row=0)

    async def start_view(self) -> None:
        contracts = await self.v_client.fetch_contracts()
        contract = (
            contracts.special_contract
            if self.relation_type == RelationType.agent
            else contracts.get_latest_contract(self.relation_type)
        )
        if contract is None:
            raise Exception(f"{chat.bold(self.relation_type.value)} is not available.")

        self.source = GamePassPageSource(contract, self.v_client.http._riot_auth, locale=self.v_locale)

        await self.start(page_number=contract.current_level)


# class GamePassPageSourceX(ListPageSource['contract.Reward']):
#     def __init__(
#         self, contracts: valorantx.Contracts, relation_type: valorantx.RelationType, riot_auth: valorantx.RiotAuth
#     ) -> None:
#         self.type = relation_type
#         self.riot_auth = riot_auth
#         self.contract = (
#             contracts.special_contract()
#             if relation_type == valorantx.RelationType.agent
#             else contracts.get_latest_contract(relation_type=relation_type)
#         )
#         super().__init__(self.contract.content.get_all_rewards(), per_page=1)

#     async def format_page(self, menu: GamePassSwitchX, page: Any):
#         reward = self.entries[menu.current_page]
#         return game_pass_e(reward, self.contract, self.type, self.riot_auth, menu.current_page, locale=menu.v_locale)


# class GamePassSwitchX(SwitchingViewX, LattePages):
#     def __init__(
#         self,
#         interaction: Interaction,
#         v_user: ValorantUser,
#         client: ValorantClient,
#         relation_type: valorantx.RelationType,
#     ) -> None:
#         super().__init__(interaction, v_user, client, row=1)
#         self.relation_type = relation_type

#     async def start_view(self, riot_auth: RiotAuth, **kwargs: Any) -> None:
#         contracts = await self.v_client.fetch_contracts()
#         self.source = GamePassPageSourceX(contracts=contracts, relation_type=self.relation_type, riot_auth=riot_auth)
#         self.current_page = self.source.contract.current_tier
#         await self.start_pages()
