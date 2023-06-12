from __future__ import annotations

from typing import TYPE_CHECKING, List

from valorantx.client import Client
from valorantx.models.match import MatchDetails as ValorantXMatchDetails, RoundResult as ValorantXRoundResult

from ...emojis import get_round_result_emoji

if TYPE_CHECKING:
    from valorantx.models.match import MatchPlayer as ValorantXMatchPlayer
    from valorantx.types.match import MatchDetails as MatchDetailsPayload


class RoundResult(ValorantXRoundResult):
    def emoji_by_player(self, player: ValorantXMatchPlayer) -> str:
        return get_round_result_emoji(self.round_result_code, self.winning_team == player.team)


class MatchDetails(ValorantXMatchDetails):
    def __init__(self, client: Client, data: MatchDetailsPayload) -> None:
        super().__init__(client, data)
        self.round_results: List[RoundResult] = [
            RoundResult(self, round_result) for round_result in data['roundResults']
        ]

    def is_draw(self) -> bool:
        blue_team = self.get_team('Blue')
        red_team = self.get_team('Red')
        if blue_team is not None and red_team is not None:
            if blue_team.rounds_won == red_team.rounds_won:
                return True
        return False
