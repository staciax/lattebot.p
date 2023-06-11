from valorantx.enums import (
    GameModeURL as GameModeURL,
    ItemType as ItemType,
    Locale as Locale,
    MissionType as MissionType,
    RelationType as RelationType,
)

# from __future__ import annotations

# from enum import Enum
# from typing import TYPE_CHECKING

# if TYPE_CHECKING:
#     from typing_extensions import Self

# __all__ = (
#     # 'RoundResultEmoji',
#     # 'ResultColor',
#     # 'DiscordValorantLocale',
# )

# class Discord2ValorantLocale(Enum):
#     en_US = 'en-US'
#     en_GB = 'en-US'
#     zh_CN = 'zh-CN'
#     zh_TW = 'zh-TW'
#     fr = 'fr-FR'
#     de = 'de-DE'
#     it = 'it-IT'
#     ja = 'ja-JP'
#     ko = 'ko-KR'
#     pl = 'pl-PL'
#     pt_BR = 'pt-BR'
#     ru = 'ru-RU'
#     es_ES = 'es-ES'
#     th = 'th-TH'
#     tr = 'tr-TR'
#     vi = 'vi-VN'
#     id = 'id-ID'

#     def __str__(self) -> str:
#         return str(self.value)

#     @classmethod
#     def from_discord(cls, value: str) -> Self:
#         value = value.replace('-', '_')
#         return cls.__members__.get(value, cls.en_US)

# class RoundResultEmoji(str, Enum):
#     defuse_loss = '<:diffuse_loss:1042809400592715816>'
#     defuse_win = '<:diffuse_win:1042809402526281778>'
#     elimination_loss = '<:elimination_loss:1042809418661761105>'
#     elimination_win = '<:elimination_win:1042809420549206026>'
#     explosion_loss = '<:explosion_loss:1042809464274812988>'
#     explosion_win = '<:explosion_win:1042809466137083996>'
#     time_loss = '<:time_loss:1042809483270832138>'
#     time_win = '<:time_win:1042809485128896582>'
#     surrendered = '<:EarlySurrender_Flag:1042829113741819996>'
#     detonate_loss = explosion_loss
#     detonate_win = explosion_win

#     def __str__(self) -> str:
#         return str(self.value)

#     @classmethod
#     def get(cls, name: str, is_win: Optional[bool] = None) -> str:
#         if name.lower() != 'surrendered':
#             return cls.__members__.get(
#                 name.lower() + ('_win' if is_win else '_loss'),
#                 (cls.time_win if is_win else cls.time_loss),
#             )
#         return cls.surrendered

# class ResultColor(IntEnum):
#     # lose = 0xFC5C5C
#     win = 0x60DCC4
#     draw = 0xCBCCD6
#     lose = 0xFC5B61
