from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from valorantx2.enums import GameModeURL

if TYPE_CHECKING:
    from valorantx2.models import MatchPlayer
    from valorantx2.models.custom.match import MatchDetails


def find_match_score_by_player(match: MatchDetails, player: MatchPlayer) -> Tuple[int, int]:
    players = match.players
    game_mode_url = match.match_info._game_mode_url
    left_team_score = 0
    right_team_score = 0
    for team in match.teams:
        if team.id == player.team_id:
            left_team_score = team.rounds_won
        else:
            right_team_score = team.rounds_won

    if game_mode_url == GameModeURL.deathmatch.value:
        if player.is_winner():
            _2nd_place = (sorted(players, key=lambda p: p.stats.kills, reverse=True)[1]) if len(players) > 1 else None
            _1st_place = player
        else:
            _2nd_place = player
            _1st_place = (sorted(players, key=lambda p: p.stats.kills, reverse=True)[0]) if len(players) > 0 else None

        left_team_score = (
            (_1st_place.stats.kills if player.is_winner() else _2nd_place is not None and _2nd_place.stats.kills)
            if _1st_place
            else left_team_score
        )
        right_team_score = (
            (_2nd_place.stats.kills if player.is_winner() else _1st_place is not None and _1st_place.stats.kills)
            if _2nd_place
            else right_team_score
        )

    return left_team_score, right_team_score


def get_match_result_by_player(match: MatchDetails, player: MatchPlayer) -> str:
    game_mode_url = match.match_info._game_mode_url
    result = 'VICTORY'

    if game_mode_url == GameModeURL.deathmatch.value:
        if player.is_winner():
            result = '1ST PLACE'
        else:
            players = sorted(match.players, key=lambda p: p.stats.kills, reverse=True)
            for i, p in enumerate(players, start=1):
                player_before = players[i - 1]
                player_after = players[i] if len(players) > i else None
                if p == player:
                    if i == 2:
                        result = '2ND PLACE'
                    elif i == 3:
                        result = '3RD PLACE'
                    else:
                        result = f'{i}TH PLACE'

                    if player_before is not None or player_after is not None:
                        if player_before.stats.kills == p.stats.kills:
                            result += ' (TIED)'
                        elif player_after is not None and player_after.stats.kills == p.stats.kills:
                            result += ' (TIED)'

    elif not player.is_winner():
        result = 'DEFEAT'

    if match.is_draw():
        result = 'DRAW'

    return result
