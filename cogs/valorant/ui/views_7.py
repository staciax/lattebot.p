from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import ui

from core.bot import LatteMiad
from core.ui.embed import MiadEmbed as Embed
from core.ui.views import ViewAuthor

from . import embeds as e

if TYPE_CHECKING:
    from core.bot import LatteMiad
    from valorantx2.models import AgentStore, StoreFront


class NewStoreFrontView(ViewAuthor):
    def __init__(
        self,
        interaction: discord.Interaction[LatteMiad],
        store_front: StoreFront,
        agent_store: AgentStore,
    ) -> None:
        super().__init__(interaction)
        self.store_front = store_front
        self.agent_store = agent_store
        self.embeds: list[Embed] = self.get_featured()

    def get_featured(self) -> list[Embed]:
        return e.store_featured_e(self.store_front.skins_panel_layout, 'STACiA')

    def get_accessories(self) -> list[Embed]:
        return e.store_accessories_e(self.store_front.accessory_store, 'STACiA')

    async def get_agents(self) -> Embed:
        recruitment_progress = await self.agent_store.fetch_featured_agent_recruitment_progress()
        if self.agent_store.featured_agent is not None:
            return e.store_agents_recruitment_e(
                self.agent_store.featured_agent,
                recruitment_progress,
                'STACiA#1234',
                locale=self.locale,
            )
        return Embed(description='No Featured Agent').purple()

    def enable_buttons(self) -> None:
        self.featured.disabled = False
        self.accessories.disabled = False
        self.agents.disabled = False

    @ui.button(label='Featured', disabled=True)
    async def featured(self, interaction: discord.Interaction[LatteMiad], button: ui.Button) -> None:
        self.enable_buttons()
        button.disabled = True
        embeds = self.embeds = self.get_featured()
        await interaction.response.edit_message(embeds=embeds, view=self)

    @ui.button(label='Accessories')
    async def accessories(self, interaction: discord.Interaction[LatteMiad], button: ui.Button) -> None:
        self.enable_buttons()
        button.disabled = True
        embeds = self.embeds = self.get_accessories()
        await interaction.response.edit_message(embeds=embeds, view=self)

    @ui.button(label='Agents')
    async def agents(self, interaction: discord.Interaction[LatteMiad], button: ui.Button) -> None:
        self.enable_buttons()
        button.disabled = True
        embeds = self.embeds = [await self.get_agents()]
        await interaction.response.edit_message(embeds=embeds, view=self)

    # @ui.button(label='expand')
    # async def resize(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
    #     embeds = []

    #     for embed in self.embeds.copy():
    #         if button.label == 'expand':
    #             embed.move_thumbnail_to_image()
    #         elif button.label == 'shrink':
    #             embed.move_image_to_thumbnail()
    #         embeds.append(embed)

    #     if button.label == 'expand':
    #         button.label = 'shrink'
    #     elif button.label == 'shrink':
    #         button.label = 'expand'

    #     await interaction.response.edit_message(embeds=embeds, view=self)

    async def start(self) -> None:
        await self.interaction.response.send_message(embeds=self.embeds, view=self)
