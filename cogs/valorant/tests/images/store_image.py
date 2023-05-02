from __future__ import annotations

import asyncio
import os
from io import BytesIO
from typing import TYPE_CHECKING, List, Tuple

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from valorantx2 import ContentTier as Rarity, SkinLevelOffer

# fmt: off
__all__ = (
    'StoreImage',
)
# fmt: on

FILEPATH = os.path.dirname(__file__)
PRIMARY_FONT = ImageFont.FreeTypeFont(os.path.join(FILEPATH, 'static', 'fonts', 'Inter-Bold.ttf'), 40)
VP_IMAGE = Image.open(os.path.join(FILEPATH, 'static', 'images', 'vp.png')).resize((65, 65)).convert('RGBA')


class StoreImage:
    def __init__(self) -> None:
        self._background: Image.Image = Image.open(os.path.join(FILEPATH, 'static', 'images', 'bg.png'))
        self._draw = ImageDraw.Draw(self._background)

    def _get_rarity_fill(self, rarity: Rarity) -> str:
        data = {
            '60bca009-4182-7998-dee7-b8a2558dc369': '#382536',  # premium
            'e046854e-406c-37f4-6607-19a9ba8426fc': '#3d3823',  # exclusive
            '0cebb8be-46d7-c12a-d306-e9907bfc5a25': '#0d3135',  # deluxe
            '12683d76-48d7-84a3-4e09-6985794f0445': '#1f3347',  # select
            '411e4a55-4e59-7757-41f0-86a53f101bb5': '#3e422e',  # ultra
        }
        return data.get(rarity.uuid)  # type: ignore

    def _rarity_background_rounded_rectangle(self, xy: Tuple[int, ...], fill: str, radius: int = 15) -> None:
        self._draw.rounded_rectangle(xy, fill=fill, radius=15)

    async def _rarity_icon_paste(self, rarity: Rarity, xy: Tuple[int, ...]) -> None:
        file = await rarity.display_icon.to_file()
        img = Image.open(file.fp)
        img = img.resize((90, 90)).convert('RGBA')
        self._background.paste(img, box=xy, mask=img)

    def _valorant_point_paste(self, xy: Tuple[int, ...]) -> None:
        self._background.paste(VP_IMAGE, xy, mask=VP_IMAGE)

    def _skin_cost_paste(self, xy: Tuple[int, ...], cost: int, *, font: ImageFont.FreeTypeFont = PRIMARY_FONT) -> None:
        self._draw.text(xy, str(cost), font=font, fill='#ffffff', align='left')

    def _skin_name_paste(
        self,
        skin: SkinLevelOffer,
        y: int,
        spacing: int,
        decrease: int,
    ) -> None:
        for line in reversed(skin.display_name.default.split(" ")):
            self._draw.text((y, spacing), line.upper(), fill='#ffffff', font=PRIMARY_FONT)
            spacing -= decrease

    async def _skin_icon_paste(self, skin: SkinLevelOffer, xy: Tuple[int, ...]) -> None:
        if skin.display_icon is None:
            return
        file = await skin.display_icon.to_file()
        img = Image.open(file.fp)
        img = img.rotate(angle=-45, expand=True, center=(255, 90))
        self._background.paste(img, xy, img)

    async def _skin_1(self, skins: List[SkinLevelOffer]) -> None:
        try:
            skin = skins[0]
        except IndexError:
            return
        else:
            self._rarity_background_rounded_rectangle((30, 25, 535, 435), fill=self._get_rarity_fill(skin.rarity))  # type: ignore
            self._valorant_point_paste((340, 55))
            self._skin_cost_paste((420, 63), skin.cost)
            await self._rarity_icon_paste(skin.rarity, (46, 42))  # type: ignore
            self._skin_name_paste(skin, 60, 355, 43)
            await self._skin_icon_paste(skin, (45, -20))

    async def _skin_2(self, skins: List[SkinLevelOffer]) -> None:
        try:
            skin = skins[1]
        except IndexError:
            return
        else:
            self._rarity_background_rounded_rectangle((570, 25, 1070, 435), fill=self._get_rarity_fill(skin.rarity))  # type: ignore
            self._valorant_point_paste((880, 55))
            self._skin_cost_paste((960, 63), skin.cost)
            await self._rarity_icon_paste(skin.rarity, (585, 42))  # type: ignore
            self._skin_name_paste(skin, 600, 355, 43)
            await self._skin_icon_paste(skin, (580, -20))

    async def _skin_3(self, skins: List[SkinLevelOffer]) -> None:
        try:
            skin = skins[2]
        except IndexError:
            return
        else:
            self._rarity_background_rounded_rectangle((30, 470, 535, 880), fill=self._get_rarity_fill(skin.rarity))  # type: ignore
            self._valorant_point_paste((340, 495))
            self._skin_cost_paste((420, 505), skin.cost)
            self._skin_name_paste(skin, 60, 795, 43)
            await self._rarity_icon_paste(skin.rarity, (46, 484))  # type: ignore
            await self._skin_icon_paste(skin, (45, 430))

    async def _skin_4(self, skins: List[SkinLevelOffer]) -> None:
        try:
            skin = skins[3]
        except IndexError:
            return
        else:
            self._rarity_background_rounded_rectangle((570, 470, 1070, 880), fill=self._get_rarity_fill(skin.rarity))  # type: ignore
            self._valorant_point_paste((880, 495))
            self._skin_cost_paste((960, 505), skin.cost)
            await self._rarity_icon_paste(skin.rarity, (585, 484))  # type: ignore
            self._skin_name_paste(skin, 600, 795, 43)
            await self._skin_icon_paste(skin, (580, 430))

    def show(self) -> None:
        self._background.show()

    def save(self, fp: str) -> None:
        self._background.save(fp)

    def to_buffer(self, fmt: str = 'PNG') -> BytesIO:
        buffer = BytesIO()
        self._background.save(buffer, format=fmt)
        buffer.seek(0)
        return buffer

    async def generate(self, skins: List[SkinLevelOffer]) -> None:
        tasks = (
            self._skin_1(skins),
            self._skin_2(skins),
            self._skin_3(skins),
            self._skin_4(skins),
        )
        await asyncio.gather(*tasks)
