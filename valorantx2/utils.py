from valorantx.utils import MISSING as MISSING

__all__ = (
    'MISSING',
    'validate_riot_id',
)


def validate_riot_id(riot_id: str) -> tuple[str, str]:
    if '#' not in riot_id:
        raise ValueError('Invalid Riot ID.')

    game_name, _, tag_line = riot_id.partition('#')

    if not game_name or not tag_line:
        raise ValueError('Invalid Riot ID.')

    if len(game_name) > 16:
        raise ValueError('Invalid Riot ID.')

    if len(tag_line) > 5:
        raise ValueError('Invalid Riot ID.')

    return game_name, tag_line
