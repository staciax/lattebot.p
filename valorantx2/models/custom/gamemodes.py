from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx.valorant_api import Localization
from valorantx.valorant_api.models import GameMode as ValorantAPIGameMode

from ...emojis import get_game_mode_emoji

if TYPE_CHECKING:
    from valorantx.valorant_api.types.gamemodes import GameMode as GameModePayload

    from ..valorant_api_cache import Cache

# fmt: off
__all__ = (
    'GameMode',
)
# fmt: on


class GameMode(ValorantAPIGameMode):
    def __init__(self, state: Cache, data: GameModePayload) -> None:
        super().__init__(state=state, data=data)

    @property
    def emoji(self) -> str:
        # return get_game_mode_emoji(self.uuid)
        return get_game_mode_emoji(self.display_name.default)

    def display_name_override(self, is_ranked: bool) -> None:
        if self.uuid == '96bd3920-4f36-d026-2b28-c683eb0bcac5':
            if is_ranked:
                self._display_name = {
                    "ar-AE": "تنافسي",
                    "de-DE": "Gewertet",
                    "en-US": "Competitive",
                    "es-ES": "Competitivo",
                    "es-MX": "Competitivo",
                    "fr-FR": "Compétition",
                    "id-ID": "Competitive",
                    "it-IT": "Competitiva",
                    "ja-JP": "コンペティティブ",
                    "ko-KR": "경쟁전",
                    "pl-PL": "Rankingowa",
                    "pt-BR": "Competitivo",
                    "ru-RU": "рейтинговaя игра",
                    "th-TH": "Competitive",
                    "tr-TR": "Rekabete dayalı",
                    "vi-VN": "thi đấu xếp hạng",
                    "zh-CN": "競技模式",
                    "zh-TW": "競技模式",
                }
            else:
                self._display_name = {
                    "ar-AE": "غير مصنف",
                    "de-DE": "Ungewertet",
                    "en-US": "Unrated",
                    "es-ES": "No competitivo",
                    "es-MX": "Normal",
                    "fr-FR": "Non classé",
                    "id-ID": "Unrated",
                    "it-IT": "Non competitiva",
                    "ja-JP": "アンレート",
                    "ko-KR": "일반전",
                    "pl-PL": "Nierankingowa",
                    "pt-BR": "Sem classificação",
                    "ru-RU": "БЕЗ Рaнгa",
                    "th-TH": "Unrated",
                    "tr-TR": "Derecesiz",
                    "vi-VN": "Đấu Thường",
                    "zh-CN": "一般模式",
                    "zh-TW": "一般模式",
                }
            self._display_name_localized = Localization(self._display_name, locale=self._state.locale)
