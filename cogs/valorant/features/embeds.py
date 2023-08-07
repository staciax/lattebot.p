import random
from pathlib import Path

import core.utils.chat_formatting as chat
import valorantx2 as valorantx
from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from valorantx2.models import Agent, Buddy, BuddyLevel, PlayerCard, Spray, SprayLevel

_ = I18n('valorant.ui.embeds', Path(__file__).resolve().parent, read_only=True)


def agent_e(agent: Agent, *, locale: valorantx.Locale = valorantx.Locale.american_english) -> Embed:
    embed = Embed(
        title=agent.display_name.from_locale(locale),
        description=chat.italics(agent.description.from_locale(locale)),
        colour=int(random.choice(agent.background_gradient_colors)[:-2], 16),
    ).purple()
    embed.set_image(url=agent.full_portrait)
    embed.set_thumbnail(url=agent.display_icon)
    embed.set_footer(
        text=agent.role.display_name.from_locale(locale),
        icon_url=agent.role.display_icon,
    )
    return embed


def buddy_e(buddy: Buddy | BuddyLevel, *, locale: valorantx.Locale = valorantx.Locale.american_english) -> Embed:
    embed = Embed().purple()
    if isinstance(buddy, valorantx.Buddy):
        embed.set_author(
            name=buddy.display_name.from_locale(locale),
            icon_url=buddy.theme.display_icon if buddy.theme is not None else None,
            url=buddy.display_icon,
        )

    elif isinstance(buddy, valorantx.BuddyLevel):
        # assert buddy.parent is not None
        embed.set_author(
            name=buddy.parent.display_name.from_locale(locale),
            url=buddy.display_icon,
            icon_url=buddy.parent.theme.display_icon if buddy.parent.theme is not None else None,
        )
    embed.set_image(url=buddy.display_icon)

    return embed


def spray_e(spray: Spray | SprayLevel, *, locale: valorantx.Locale = valorantx.Locale.american_english) -> Embed:
    embed = Embed().purple()

    if isinstance(spray, valorantx.Spray):
        embed.set_author(
            name=spray.display_name.from_locale(locale),
            url=spray.display_icon,
            icon_url=spray.theme.display_icon if spray.theme is not None else None,
        )
        embed.set_image(url=spray.animation_gif or spray.full_transparent_icon or spray.display_icon)

    elif isinstance(spray, valorantx.SprayLevel):
        # assert spray.parent is not None
        embed.set_author(
            name=spray.parent.display_name.from_locale(locale),
            icon_url=spray.parent.theme.display_icon if spray.parent.theme is not None else None,
            url=spray.display_icon,
        )
        embed.set_image(
            url=spray.parent.animation_gif
            or spray.parent.full_transparent_icon
            or spray.parent.display_icon
            or spray.display_icon
        )

    return embed


def player_card_e(player_card: PlayerCard, *, locale: valorantx.Locale = valorantx.Locale.american_english) -> Embed:
    embed = Embed().purple()
    embed.set_author(
        name=player_card.display_name.from_locale(locale),
        icon_url=player_card.theme.display_icon if player_card.theme is not None else None,
        url=player_card.large_art,
    )
    if player_card.large_art is not None:
        embed.set_image(url=player_card.large_art)
    return embed
