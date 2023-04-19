from __future__ import annotations

# import datetime
# import random
from typing import TYPE_CHECKING, Iterable, List, Tuple, Union

import discord
import valorantx2 as valorantx
from discord.utils import format_dt
from valorantx2.auth import RiotAuth
from valorantx2.models.store import SkinsPanelLayout
from valorantx2.models.weapons import SkinLevelOffer

import core.utils.chat_formatting as chat

from .emojis import Point

if TYPE_CHECKING:
    from typing_extensions import Self


class Embed(discord.Embed):
    def __init__(
        self,
        color: Union[discord.Color, int] = 0xFFFFFF,
        fields: Iterable[Tuple[str, str]] = (),
        field_inline: bool = False,
        **kwargs,
    ):
        super().__init__(color=color, **kwargs)
        for n, v in fields:
            self.add_field(name=n, value=v, inline=field_inline)

    def purple(self) -> Self:
        self.colour = 0xC0AEE0
        return self

    def dark_purple(self) -> Self:
        self.colour = 0x8B7DB5
        return self


def skin_e(
    skin: valorantx.Skin | valorantx.SkinLevel | valorantx.SkinChroma | SkinLevelOffer,  # valorantx.SkinNightMarket
    *,
    locale: valorantx.Locale,
) -> Embed:
    embed = Embed(
        title=f"{skin.rarity.emoji} {chat.bold(skin.display_name_localized(locale))}",  # type: ignore
    ).purple()

    if isinstance(skin, SkinLevelOffer):
        embed.description = f'{Point.valorant} {chat.bold(str(skin.cost))}'

    # embed.description = (
    #     f'PointEmoji.valorant {chat.bold(str(skin.discount_price))}\n'
    #     f'PointEmoji.valorant {chat.strikethrough(str(skin.price))} (-{skin.discount_percent}%)'
    # )

    if skin.display_icon is not None:
        embed.url = skin.display_icon.url
        embed.set_thumbnail(url=skin.display_icon)

    if skin.rarity is not None:
        embed.colour = int(skin.rarity.highlight_color[0:6], 16)

    return embed


def store_e(
    panel: SkinsPanelLayout, riot_auth: RiotAuth, *, locale: valorantx.Locale = valorantx.Locale.english
) -> List[Embed]:
    embeds = [
        Embed(
            description='Daily store for {user}\n'.format(user=chat.bold(riot_auth.display_name))
            + f"Resets {format_dt(panel.remaining_time, style='R')}",
        ).purple(),
    ]

    for skin in panel.skins:
        embeds.append(skin_e(skin, locale=locale))

    return embeds
