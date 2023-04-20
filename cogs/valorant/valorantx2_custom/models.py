# from __future__ import annotations

# from typing import Any, Dict, List, Mapping, Optional, Tuple,  Union

# from .enums import GameModeEmoji, PointEmoji, RoundResultEmoji

# from valorantx2 import CurrencyType, GameModeType, Localization
# from valorantx2.models import match

# __all__: Tuple[str, ...] = (
#     'Currency',
#     'MatchRoundResult',
#     'GameMode',
#     'MatchDetails',
#     'MatchDetails',
# )

# class Currency(valorantx.Currency):
#     @property
#     def emoji(self) -> str:
#         return str(PointEmoji.valorant) if self.uuid == str(CurrencyType.valorant) else str(PointEmoji.radianite)

# class MatchRoundResult(match.RoundResult):
#     @property
#     def emoji(self) -> str:
#         return RoundResultEmoji.get(str(self.result_code), self.winning_team() == self.match.me.team)

#     def emoji_by_player(self, player: valorantx.MatchPlayer) -> str:
#         return RoundResultEmoji.get(str(self.result_code), self.winning_team() == player.team)


# class GameMode(valorantx.GameMode):
#     def __init__(self, client: Client, data: Mapping[str, Any], **kwargs) -> None:
#         super().__init__(client=client, data=data)
#         self._display_name: Union[str, Dict[str, str]] = data['displayName']
#         self._is_ranked: bool = kwargs.get('is_ranked', False)
#         self.__display_name_override()

#     @property
#     def emoji(self) -> str:
#         return GameModeEmoji.get(self.display_name.default)

#     def is_ranked(self) -> bool:
#         """:class: `bool` Returns whether the game mode is ranked."""
#         return self._is_ranked

#     def __display_name_override(self) -> None:
#         if self.uuid == '96bd3920-4f36-d026-2b28-c683eb0bcac5':
#             if self._is_ranked:
#                 self._display_name = {
#                     "ar-AE": "تنافسي",
#                     "de-DE": "Gewertet",
#                     "en-US": "Competitive",
#                     "es-ES": "Competitivo",
#                     "es-MX": "Competitivo",
#                     "fr-FR": "Compétition",
#                     "id-ID": "Competitive",
#                     "it-IT": "Competitiva",
#                     "ja-JP": "コンペティティブ",
#                     "ko-KR": "경쟁전",
#                     "pl-PL": "Rankingowa",
#                     "pt-BR": "Competitivo",
#                     "ru-RU": "рейтинговaя игра",
#                     "th-TH": "Competitive",
#                     "tr-TR": "Rekabete dayalı",
#                     "vi-VN": "thi đấu xếp hạng",
#                     "zh-CN": "競技模式",
#                     "zh-TW": "競技模式",
#                 }
#             else:
#                 self._display_name = {
#                     "ar-AE": "غير مصنف",
#                     "de-DE": "Ungewertet",
#                     "en-US": "Unrated",
#                     "es-ES": "No competitivo",
#                     "es-MX": "Normal",
#                     "fr-FR": "Non classé",
#                     "id-ID": "Unrated",
#                     "it-IT": "Non competitiva",
#                     "ja-JP": "アンレート",
#                     "ko-KR": "일반전",
#                     "pl-PL": "Nierankingowa",
#                     "pt-BR": "Sem classificação",
#                     "ru-RU": "БЕЗ Рaнгa",
#                     "th-TH": "Unrated",
#                     "tr-TR": "Derecesiz",
#                     "vi-VN": "Đấu Thường",
#                     "zh-CN": "一般模式",
#                     "zh-TW": "一般模式",
#                 }
#             self._display_name_localized = Localization(self._display_name, locale=self._client.locale)


# class MatchDetails(valorantx.MatchDetails):
#     def __init__(self, client: Client, data: Any) -> None:
#         super().__init__(client=client, data=data)
#         self._round_results: List[MatchRoundResult] = (
#             [MatchRoundResult(self, data) for data in data['roundResults']] if data.get('roundResults') else []
#         )

#     @property
#     def game_mode(self) -> Optional[GameMode]:
#         """:class:`GameMode`: The game mode this match was played in."""
#         return self._client.get_game_mode(uuid=GameModeType.from_url(self._game_mode), is_ranked=self._is_ranked)
