from discord import Locale as DiscordLocale
from valorantx import Locale as ValorantLocale


class locale_converter:  # ignore naming rule
    @staticmethod
    def to_valorant(locale: DiscordLocale) -> ValorantLocale:
        return getattr(ValorantLocale, locale.name, ValorantLocale.american_english)

    @staticmethod
    def to_discord(locale: ValorantLocale) -> DiscordLocale:
        return getattr(DiscordLocale, locale.name, DiscordLocale.american_english)
