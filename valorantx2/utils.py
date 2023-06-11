from discord import Locale as DiscordLocale
from valorantx import Locale as ValorantLocale


def locale_converter(discord_locale: DiscordLocale) -> ValorantLocale:
    return getattr(ValorantLocale, discord_locale.name, ValorantLocale.american_english)
