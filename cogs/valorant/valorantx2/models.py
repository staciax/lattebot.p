# from __future__ import annotations

# from typing import Any, List, Optional

# from .enums import RoundResultEmoji

# from valorantx2 import GameModeType
# from valorantx2.models import match

# __all__ = (
#     'MatchRoundResult',
#     'MatchDetails',
#     'MatchDetails',
# )

# class MatchRoundResult(match.RoundResult):
#     @property
#     def emoji(self) -> str:
#         return RoundResultEmoji.get(str(self.result_code), self.winning_team() == self.match.me.team)

#     def emoji_by_player(self, player: valorantx.MatchPlayer) -> str:
#         return RoundResultEmoji.get(str(self.result_code), self.winning_team() == player.team)

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
