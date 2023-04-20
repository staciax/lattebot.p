from __future__ import annotations

# import datetime
# import random
from typing import TYPE_CHECKING, Iterable, List, Tuple, Union

import discord
import valorantx2 as valorantx
from discord.utils import format_dt
from valorantx2.auth import RiotAuth
from valorantx2.models.store import BonusStore, SkinsPanelLayout
from valorantx2.models.weapons import SkinLevelOffer

import core.utils.chat_formatting as chat

from ..valorantx2_custom.emojis import VALORANT_POINT_EMOJI

if TYPE_CHECKING:
    from typing_extensions import Self


class Embed(discord.Embed):
    def __init__(
        self,
        color: Union[discord.Color, int] = 0xFFFFFF,
        fields: Iterable[Tuple[str, str]] = (),
        field_inline: bool = False,
        **kwargs,
    ):
        super().__init__(color=color, **kwargs)
        for n, v in fields:
            self.add_field(name=n, value=v, inline=field_inline)

    def purple(self) -> Self:
        self.colour = 0xC0AEE0
        return self

    def dark_purple(self) -> Self:
        self.colour = 0x8B7DB5
        return self


def skin_e(
    skin: valorantx.Skin | valorantx.SkinLevel | valorantx.SkinChroma | SkinLevelOffer,  # valorantx.SkinNightMarket
    *,
    locale: valorantx.Locale,
) -> Embed:
    embed = Embed(
        title=f"{skin.rarity.emoji} {chat.bold(skin.display_name_localized(locale))}",  # type: ignore
    ).purple()

    if isinstance(skin, SkinLevelOffer):
        embed.description = f'{VALORANT_POINT_EMOJI} {chat.bold(str(skin.cost))}'

    # embed.description = (
    #     f'PointEmoji.valorant {chat.bold(str(skin.discount_price))}\n'
    #     f'PointEmoji.valorant {chat.strikethrough(str(skin.price))} (-{skin.discount_percent}%)'
    # )

    if skin.display_icon is not None:
        embed.url = skin.display_icon.url
        embed.set_thumbnail(url=skin.display_icon)

    if skin.rarity is not None:
        embed.colour = int(skin.rarity.highlight_color[0:6], 16)

    return embed


def store_e(
    panel: SkinsPanelLayout, riot_auth: RiotAuth, *, locale: valorantx.Locale = valorantx.Locale.english
) -> List[Embed]:
    embeds = [
        Embed(
            description='Daily store for {user}\n'.format(user=chat.bold(riot_auth.display_name))
            + f"Resets {format_dt(panel.remaining_time, style='R')}",
        ).purple(),
    ]

    for skin in panel.skins:
        embeds.append(skin_e(skin, locale=locale))

    return embeds


def nightmarket_e(bonus: BonusStore, riot_auth: RiotAuth, *, locale: valorantx.Locale) -> List[Embed]:
    embeds = [
        Embed(
            description=f'NightMarket for {chat.bold(riot_auth.display_name)}\n'
            # f'Expires {format_dt(bonus.expire_at, style="R")}',
        ).purple()
    ]
    # for skin in bonus.skins:
    #     embeds.append(skin_e(skin, locale=locale))

    return embeds


def wallet_e(wallet: valorantx.Wallet, riot_auth: RiotAuth, *, locale: valorantx.Locale) -> Embed:
    # vp = wallet.valorant_points
    # rad = wallet.radiant_points

    # vp_name = vp.name_localizations.from_locale(str(locale))

    embed = Embed(title=f'{riot_auth.display_name} Point:').purple()

    # embed.add_field(
    #     name=f'{(vp_name if vp_name != "VP" else "Valorant")}',
    #     value=f'{vp.emoji} {wallet.valorant_points}',  # type: ignore
    # )
    # embed.add_field(
    #     name=f'{rad.name_localizations.from_locale(str(locale)).removesuffix(" Points")}',
    #     value=f'{rad.emoji} {wallet.radiant_points}',  # type: ignore
    # )
    return embed


# def game_pass_e(
#     reward: contract.Reward,
#     contract: contract.ContractU,
#     relation_type: valorantx.RelationType,
#     riot_auth: RiotAuth,
#     page: int,
#     *,
#     locale: Optional[valorantx.Locale] = None,
# ) -> discord.Embed:

#     item = reward.get_item()

#     if relation_type is valorantx.RelationType.agent:
#         display_name = 'Agent'
#     elif relation_type is valorantx.RelationType.event:
#         display_name = 'Eventpass'
#     else:
#         display_name = 'Battlepass'
#     embed = discord.Embed(
#         title='{gamepass} for {display_name}'.format(gamepass=display_name, display_name=bold(riot_auth.display_name))
#     )
#     embed.set_footer(
#         text='TIER {tier} | {gamepass}'.format(
#             tier=page + 1, gamepass=contract.name_localizations.from_locale(str(locale))
#         )
#     )

#     if item is not None:
#         embed.description = '{item}'.format(item=item.display_name)
#         if not isinstance(item, valorantx.PlayerTitle):
#             if item.display_icon is not None:
#                 if isinstance(item, valorantx.SkinLevel):
#                     embed.set_image(url=item.display_icon)
#                 elif isinstance(item, valorantx.PlayerCard):
#                     embed.set_image(url=item.wide_icon)
#                 # elif isinstance(item, valorantx.Agent):
#                 #     embed.set_image(url=item.full_portrait_v2 or item.full_portrait)
#                 else:
#                     embed.set_thumbnail(url=item.display_icon)

#     return embed


# def mission_e(
#     contracts: valorantx.Contracts, riot_auth: RiotAuth, *, locale: Optional[valorantx.Locale] = None
# ) -> discord.Embed:
#     daily = []
#     weekly = []
#     tutorial = []
#     npe = []

#     all_completed = True

#     daily_format = '{0} | **+ {1.xp:,} XP**\n- **`{1.progress}/{1.target}`**'
#     for mission in contracts.missions:
#         title = mission.title_localizations.from_locale(str(locale))
#         if mission.type == MissionType.daily:
#             daily.append(daily_format.format(title, mission))
#         elif mission.type == MissionType.weekly:
#             weekly.append(daily_format.format(title, mission))
#         elif mission.type == MissionType.tutorial:
#             tutorial.append(daily_format.format(title, mission))
#         elif mission.type == MissionType.npe:
#             npe.append(daily_format.format(title, mission))

#         if not mission.is_completed():
#             all_completed = False

#     embed = Embed(title='{display_name} Mission:'.format(display_name=riot_auth.display_name))
#     if all_completed:
#         embed.colour = 0x77DD77

#     if len(daily) > 0:
#         embed.add_field(
#             name=f"**Daily**",
#             value='\n'.join(daily),
#             inline=False,
#         )

#     if len(weekly) > 0:

#         embed.add_field(
#             name=f"**Weekly**",
#             value='\n'.join(weekly)
#             + '\n\n Refill Time: {refill_time}'.format(
#                 refill_time=format_relative(contracts.mission_metadata.weekly_refill_time)
#                 if contracts.mission_metadata.weekly_refill_time is not None
#                 else '-'
#             ),
#         )

#     if len(tutorial) > 0:
#         embed.add_field(
#             name=f"**Tutorial**",
#             value='\n'.join(tutorial),
#             inline=False,
#         )

#     if len(npe) > 0:
#         embed.add_field(
#             name=f"**NPE**",
#             value='\n'.join(npe),
#             inline=False,
#         )

#     return embed
