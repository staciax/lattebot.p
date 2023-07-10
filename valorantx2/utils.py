from discord.enums import Locale as DiscordLocale
from valorantx import Locale as ValorantLocale
from valorantx.utils import MISSING as MISSING

__all__ = (
    'locale_converter',
    'MISSING',
)


class locale_converter:
    @staticmethod
    def to_valorant(locale: DiscordLocale) -> ValorantLocale:
        return getattr(ValorantLocale, locale.name, ValorantLocale.american_english)

    @staticmethod
    def to_discord(locale: ValorantLocale) -> DiscordLocale:
        return getattr(DiscordLocale, locale.name, DiscordLocale.american_english)


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
