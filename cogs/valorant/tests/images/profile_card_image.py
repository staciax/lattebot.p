from __future__ import annotations

import asyncio
import os
import sys
from enum import Enum
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if sys.version_info >= (3, 10):
    import cchardet as chardet  # type: ignore
else:
    import chardet

if TYPE_CHECKING:
    from valorantx.valorant_api.models import LevelBorder, PlayerCard, PlayerTitle, Tier


FILEPATH = os.path.dirname(__file__)
FONT_DINNEXTWIG_BOLD_19 = ImageFont.truetype(FILEPATH + '\\static\\fonts\\DINNextW1G-Bold.otf', size=19)
FONT_DINNEXTWIG_13 = ImageFont.truetype(FILEPATH + '\\static\\fonts\\DINNextW1G-Regular.otf', size=13)
FONT_BENIBOLD_36 = ImageFont.truetype(FILEPATH + '\\static\\fonts\\BeniBold.ttf', size=36)
FONT_712_SERIF_20 = ImageFont.truetype(FILEPATH + '\\static\\fonts\\712_serif.ttf.ttf', size=20)
FONT_712_SERIF_30 = ImageFont.truetype(FILEPATH + '\\static\\fonts\\712_serif.ttf.ttf', size=30)


class StatusType(str, Enum):
    available = 0
    away = 1
    offline = 2
    in_match = 3

    def __int__(self) -> int:
        return self.value


class StatusColor(str, Enum):
    available = '#63c0b5'
    away = '#de997d'
    offline = '#8a8b8f'
    in_match = '#4e98cc'

    def __str__(self) -> str:
        return self.value


class TextColor(str, Enum):
    username = "#252627"
    player_title = "#64666a"
    tagline = "#64666a"
    level = "#e8e1cd"

    def __str__(self) -> str:
        return self.value


class ProfileCardImage:
    def __init__(self, status_type: StatusType = StatusType.available) -> None:
        self._background: Image.Image = Image.open(FILEPATH + f'\\static\\images\\profile_card_{status_type.name}.png')
        self._draw = ImageDraw.Draw(self._background)

    async def _player_card_paste(self, card: PlayerCard) -> None:
        if card.small_art is None:
            return

        file = await card.small_art.to_file()
        img = Image.open(file.fp)
        img = img.resize((62, 62), Image.LANCZOS).convert('RGBA')

        self._background.paste(img, (234, 10), mask=img)

    async def _level_border_paste(self, level_border: LevelBorder) -> None:
        file_small = await level_border.small_player_card_appearance.to_file()
        level_small = Image.open(file_small.fp)
        level_small = level_small.convert('RGBA')
        self._background.paste(level_small, (225, 3), mask=level_small)

        file_level_number = await level_border.level_number_appearance.to_file()
        level_border_number = Image.open(file_level_number.fp)
        level_border_number = level_border_number.convert('RGBA')
        self._background.paste(level_border_number, (226, 62), mask=level_border_number)  # 63

    async def _tier_icon_paste(self, tier: Tier) -> None:
        if tier.small_icon is None:
            return

        file = await tier.small_icon.to_file()
        img = Image.open(file.fp)
        img = img.convert('RGBA')
        self._background.paste(img, (19, 121), mask=img)

    def _display_name_text(self, username: str, tagline: str) -> None:
        tagline_y = 44

        # username detection encoding utf-8
        if chardet.detect(username.encode('utf-8'))['encoding'] == 'utf-8':
            font_username = FONT_712_SERIF_30
        else:
            font_username = FONT_DINNEXTWIG_BOLD_19

        # tagline detection encoding utf-8
        if chardet.detect(tagline.encode('utf-8'))['encoding'] == 'utf-8':
            font_tagline = FONT_712_SERIF_20
            tagline_y += 1
        else:
            font_tagline = FONT_DINNEXTWIG_13

        # username text
        textlength = self._draw.textlength(username, font=font_username)
        self._draw.text((26, 39), username, font=font_username, fill=TextColor.username)

        # tagline text
        tagline_x = 30 + round(textlength)
        self._draw.text((tagline_x, tagline_y), f"#{tagline}", font=font_tagline, fill=TextColor.tagline)

    def _player_tile_text(self, title: PlayerTitle) -> None:
        self._draw.text((26, 63), title.text.default.upper(), font=FONT_DINNEXTWIG_13, fill=TextColor.player_title)

    def _competitive_rank_text(self, tier: Tier) -> None:
        self._draw.text((92, 141), tier.name.default.upper(), font=FONT_BENIBOLD_36, fill=f"#{tier.color}")

    def _level_text(self, value: int) -> None:
        self._draw.text(
            (264, 82), str(value), font=FONT_DINNEXTWIG_13, fill=TextColor.level, align='center', anchor='ms'
        )
