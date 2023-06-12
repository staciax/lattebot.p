from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, Tuple, Union

from discord import Colour as DiscordColour, Embed as DiscordEmbed
from discord.types.embed import EmbedType

if TYPE_CHECKING:
    from typing_extensions import Self

# fmt: off
__all__ = (
    'MiadEmbed',
    'count_python',
)
# fmt: on


# - thanks for stella_bot: https://github.com/InterStella0/stella_bot


class MiadEmbed(DiscordEmbed):
    def __init__(
        self,
        *,
        colour: Optional[Union[int, DiscordColour]] = 0xFFFFFF,
        color: Optional[Union[int, DiscordColour]] = 0xFFFFFF,
        title: Optional[Any] = None,
        type: EmbedType = 'rich',
        url: Optional[Any] = None,
        description: Optional[Any] = None,
        timestamp: Optional[datetime.datetime] = None,
        fields: Iterable[Tuple[str, str]] = (),
        field_inline: bool = False,
        custom_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            color=color, colour=colour, title=title, type=type, description=description, url=url, timestamp=timestamp
        )
        self.custom_id: Optional[str] = custom_id
        self.extra: Dict[str, Any] = kwargs
        for n, v in fields:
            self.add_field(name=n, value=v, inline=field_inline)

    def secondary(self) -> Self:
        self.colour = 0x111111
        return self

    def tertiary(self) -> Self:
        self.colour = 0x222222
        return self

    def purple(self) -> Self:
        self.colour = 0xC0AEE0
        return self

    def dark_purple(self) -> Self:
        self.colour = 0x8B7DB5
        return self

    def dark(self) -> Self:
        self.colour = 0x0F1923
        return self

    def success(self) -> Self:
        self.colour = 0x8BE28B
        return self

    def error(self) -> Self:
        self.colour = 0xFF6961
        return self

    def warning(self) -> Self:
        self.colour = 0xFDFD96
        return self

    def info(self) -> Self:
        self.colour = 0x60DCC4
        return self

    def danger(self) -> Self:
        self.colour = 0xFC5C5C
        return self

    def light(self) -> Self:
        self.colour = 0xCBCCD6
        return self


def reading_recursive(root: str, /) -> Iterable[int]:
    for x in os.listdir(root):
        if os.path.isdir(x):
            yield from reading_recursive(root + "/" + x)
            for y in os.listdir(root + "/" + x):
                if os.path.isdir(root + "/" + x + "/" + y):
                    yield from reading_recursive(root + "/" + x + "/" + y)
        else:
            if x.endswith(".py") and not root.startswith('./_'):
                with open(f"{root}/{x}", encoding="utf-8") as r:
                    yield len(r.readlines())


def count_python(root: str) -> int:
    return sum(reading_recursive(root))
