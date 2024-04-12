from __future__ import annotations

import contextlib
import random
from datetime import UTC
from typing import TYPE_CHECKING

import discord

from core.ui.embed import MiadEmbed as Embed
from core.ui.views import BaseView
from core.utils import chat_formatting as chat

from ..utils import locale_converter

# fmt: off
__all__ = (
    'PatchNoteView',
)
# fmt: on

if TYPE_CHECKING:
    from core.bot import LatteMaid
    from valorantx2 import PatchNote


def patch_note_e(pn: PatchNote, banner_url: str | None = None) -> Embed:
    embed = Embed(
        title=pn.title,
        timestamp=pn.timestamp.replace(tzinfo=UTC),
        url=pn.url,
        description=chat.italics(pn.description),
    )
    embed.set_image(url=(banner_url or pn.banner))
    return embed


class PatchNoteView(BaseView):
    def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
        super().__init__()
        self.interaction: discord.Interaction[LatteMaid] = interaction
        self.bot: LatteMaid = interaction.client

    async def _init(self) -> Embed:
        valorant_client = self.bot.valorant_client
        patch_notes = await valorant_client.fetch_patch_notes(locale_converter.to_valorant(self.interaction.locale))
        latest = patch_notes.get_latest_patch_note()

        if latest is None:
            raise ValueError('Not found latest patch note')

        pns = await valorant_client.fetch_patch_note_from_site(latest.url)
        embed = patch_note_e(latest, pns.banner.url if pns.banner is not None else None)

        if embed.image.url is not None:
            with contextlib.suppress(Exception):
                palettes = await self.bot.fetch_palettes(latest.uid, embed.image.url, 5)
                embed.colour = random.choice(palettes)

        self.url_button(label=patch_notes.see_article_title, url=latest.url, emoji=str(self.bot.emoji.link_standard))
        return embed

    async def start(self) -> None:
        await self.interaction.response.defer()
        embed = await self._init()
        await self.interaction.followup.send(embed=embed, view=self)
