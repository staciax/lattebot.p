from __future__ import annotations

import enum
from dataclasses import dataclass
from io import BytesIO
from typing import Optional, Union

import chardet
import requests
from PIL import Image, ImageDraw, ImageFont


@dataclass
class Profile:
    username: Optional[str]
    tagline: Optional[str]
    title: Optional[str]
    player_card: str
    rank: str
    rank_color: Union[str, int]
    rank_icon: str
    level: int
    level_border: str
    level_border_number: str


class Colors(str, enum.Enum):
    username = '#252627'
    tagline = '#64666a'
    title = '#64666a'
    level = '#e8e1cd'

    def __str__(self) -> str:
        return self.value


class StatusColor(str, enum.Enum):
    available = "#63c0b5"
    away = "#de997d"
    offline = "#8a8b8f"
    in_match = "#4e98cc"

    def __str__(self) -> str:
        return self.value


def profile(player: Profile):
    # ascii font
    font_username = ImageFont.truetype(font='fonts/DINNextW1G-Bold.otf', size=19)
    font_tagline = ImageFont.truetype(font='fonts/DINNextW1G-Regular.otf', size=13)
    font_rank = ImageFont.truetype(font='fonts/BeniBold.ttf', size=36)
    font_title = ImageFont.truetype(font='fonts/DINNextW1G-Regular.otf', size=13)

    session = requests.Session()

    # open image
    background = Image.open('backgrounds/profile_card_available_2.png')

    # playercard
    r = session.get(player.player_card)
    card = Image.open(BytesIO(r.content)).resize((62, 62), Image.Resampling.LANCZOS).convert('RGBA')

    # rank icon
    r = session.get(player.rank_icon)
    rank_icon = Image.open(BytesIO(r.content)).convert('RGBA')

    # level_border
    r = session.get(player.level_border)
    level_border = Image.open(BytesIO(r.content)).convert('RGBA')

    # level_border_number
    r = session.get(player.level_border_number)
    level_border_number = Image.open(BytesIO(r.content)).convert('RGBA')

    # draw
    draw = ImageDraw.Draw(background)

    # paste image
    background.paste(card, (234, 10), card)
    background.paste(level_border, (225, 3), level_border)
    background.paste(level_border_number, (226, 62), level_border_number)  # 63
    background.paste(rank_icon, (19, 121), rank_icon)

    # tagline position
    tagline_y = 44

    # username detection utf-8
    if chardet.detect(player.username.encode('utf-8'))['encoding'] == 'utf-8':
        font_username = ImageFont.truetype(font='fonts/712_serif.ttf', size=30)

    # tagline detection utf-8
    if chardet.detect(player.tagline.encode('utf-8'))['encoding'] == 'utf-8':
        font_tagline = ImageFont.truetype(font='fonts/712_serif.ttf', size=20)
        tagline_y += 1

    # username
    textlength = draw.textlength(player.username, font=font_username)
    draw.text((26, 39), player.username, font=font_username, fill=str(Colors.username))

    # tagline
    tagline_x = 30 + round(textlength)
    draw.text((tagline_x, tagline_y), f"#{player.tagline}", font=font_tagline, fill=str(Colors.tagline))

    # player tile
    draw.text((26, 63), player.title, font=font_title, fill=Colors.title.value)

    # current tier
    draw.text((92, 141), player.rank, font=font_rank, fill=f"#{player.rank_color}")

    # level
    draw.text((264, 82), str(player.level), font=font_title, fill=Colors.level.value, align='center', anchor='ms')

    background.show()


profile(
    Profile(
        'STACIA',
        '12345',
        'TOXIC',
        'https://media.valorant-api.com/playercards/1ec054a0-4184-8802-57fb-0ab81599befd/smallart.png',
        'RADIANT',
        'ffffaaff',
        'https://media.valorant-api.com/competitivetiers/e4e9a692-288f-63ca-7835-16fbf6234fda/24/smallicon.png',
        '480',
        'https://media.valorant-api.com/levelborders/6694d7f7-4ab9-8545-5921-35a9ea8cec24/smallplayercardappearance.png',
        'https://media.valorant-api.com/levelborders/6694d7f7-4ab9-8545-5921-35a9ea8cec24/levelnumberappearance.png',
    )
)
