from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import discord

from core.i18n import I18n
from core.ui.embed import MiadEmbed as Embed
from core.utils import chat_formatting as chat
from valorantx2.enums import GameModeURL, RoundResultCode

from ..utils import locale_converter

if TYPE_CHECKING:
    # from core.bot import LatteMaid
    from valorantx2.models import MatchPlayer
    from valorantx2.models.custom.match import MatchDetails

_ = I18n('valorant.ui.carrier', Path(__file__).resolve().parent, read_only=True)


def find_match_score_by_player(match: MatchDetails, player: MatchPlayer) -> tuple[int, int]:
    left_team_score = 0
    right_team_score = 0

    players = match.players
    game_mode_url = match.match_info._game_mode_url
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
    result = _('VICTORY')

    if game_mode_url == GameModeURL.deathmatch.value:
        if player.is_winner():
            result = _('1ST PLACE')
        else:
            players = sorted(match.players, key=lambda p: p.stats.kills, reverse=True)
            for i, p in enumerate(players, start=1):
                player_before = players[i - 1]
                player_after = players[i] if len(players) > i else None
                if p == player:
                    if i == 2:
                        result = _('2ND PLACE')
                    elif i == 3:
                        result = _('3RD PLACE')
                    else:
                        result = _('{i}TH PLACE').format(i=i)

                    if player_before is not None or player_after is not None:
                        if player_before.stats.kills == p.stats.kills:
                            result += _(' (TIED)')
                        elif player_after is not None and player_after.stats.kills == p.stats.kills:
                            result += _(' (TIED)')

    elif not player.is_winner():
        result = _('DEFEAT')

    if match.is_draw():
        result = _('DRAW')

    return result


def match_history_select_e(
    match: MatchDetails,
    puuid: str,
    *,
    locale: discord.Locale = discord.Locale.american_english,
) -> Embed:
    me = match.get_player(puuid)
    if me is None:
        return Embed(description='You are not in this match.').warning()

    vlocale = locale_converter.to_valorant(locale)
    agent = me.agent
    game_mode = match.match_info.game_mode
    match_map = match.match_info.map
    tier = me.competitive_tier

    left_team_score, right_team_score = find_match_score_by_player(match, me)
    result = get_match_result_by_player(match, me)

    embed = Embed(
        # title=match.game_mode.emoji + ' ' + match.game_mode.display_name,
        description="{kda} {kills}/{deaths}/{assists}".format(
            # tier=((tier.emoji + ' ') if match.match_info.queue_id == 'competitive' else ''),
            kda=chat.bold('KDA'),
            kills=me.stats.kills,
            deaths=me.stats.deaths,
            assists=me.stats.assists,
        ),
        timestamp=match.started_at,
    )

    if me.is_winner() and not match.is_draw():
        embed.info()
    elif match.is_draw():
        embed.light()
    else:
        embed.danger()

    # elif not me.is_winner() and not match.is_draw():
    #     embed.danger()

    # if game_mode is not None:
    #     embed.title = game_mode.emoji + ' ' + game_mode.display_name.from_locale(locale)

    embed.set_author(
        name=f'{result} {left_team_score} - {right_team_score}',
        icon_url=agent.display_icon if agent is not None else None,
    )

    if match_map is not None and match_map.splash is not None and game_mode is not None:
        embed.set_thumbnail(url=match_map.splash)

        if gamemode_name_override := getattr(match.match_info.game_mode, 'display_name_override', None):
            gamemode_name_override(match.match_info.is_ranked())

        embed.set_footer(
            text=f'{game_mode.display_name.from_locale(vlocale)} • {match_map.display_name.from_locale(vlocale)}',
            icon_url=tier.large_icon
            if tier is not None and match.match_info.queue_id == 'competitive'
            else game_mode.display_icon,
        )
    return embed


# match details embed
# below is so fk ugly code but i don't have any idea to make it better :(
# but it works so i don't care
# if only desktop version, i can make it better but both desktop and mobile version is so fk ugly code


class MatchDetailsEmbed:
    def __init__(self, match: MatchDetails) -> None:
        self.match = match

    def __template_e(
        self,
        player: MatchPlayer,
        performance: bool = False,
        *,
        locale: discord.Locale = discord.Locale.american_english,
    ) -> Embed:
        vlocale = locale_converter.to_valorant(locale)
        match = self.match
        match_map = match.match_info.map
        gamemode = match.match_info.game_mode
        left_team_score, right_team_score = find_match_score_by_player(match, player)
        result = get_match_result_by_player(match, player)

        embed = Embed(
            title='{mode} {map} // {won}:{lose}'.format(
                mode=gamemode.emoji if gamemode is not None else '',  # type: ignore
                map=match_map.display_name.from_locale(vlocale) if match_map is not None else match.match_info.map_id,
                won=left_team_score,
                lose=right_team_score,
            ),
            timestamp=match.started_at,
        )

        embed.set_author(
            name='{author} // {page}'.format(
                author=player.display_name,
                page=(
                    gamemode.display_name.from_locale(vlocale) if gamemode is not None and not performance else 'Performance'
                ),
            ),
            icon_url=player.agent.display_icon_small if player.agent is not None else None,
        )

        embed.set_footer(text=result)

        if player.is_winner() and not match.is_draw():
            embed.info()
        elif match.is_draw():
            embed.light()
        else:
            embed.danger()

        return embed

    # desktop

    def __build_page_1_d(
        self,
        match: MatchDetails,
        player: MatchPlayer,
        *,
        locale: discord.Locale,
    ) -> Embed:
        vlocale = locale_converter.to_valorant(locale)
        embed = self.__template_e(player, locale=locale)
        members = sorted(match.get_members(player), key=lambda p: p.stats.acs, reverse=True)
        opponents = sorted(match.get_opponents(player), key=lambda p: p.stats.acs, reverse=True)
        if match.match_info._game_mode_url != GameModeURL.deathmatch.value:
            # MY TEAM
            myteam = '\n'.join([self.__display_player(player, p) for p in members])

            # page 1
            embed.add_field(
                name='MY TEAM',
                value=myteam,
            )
            embed.add_field(
                name='ACS',
                value="\n".join([self.__display_acs(p) for p in members]),
            )
            embed.add_field(name='KDA', value="\n".join([str(p.stats.kda) for p in members]))

            # ENEMY TEAM
            enemyteam = '\n'.join([self.__display_player(player, p, bold=False) for p in opponents])

            # page 1
            embed.add_field(
                name='ENEMY TEAM',
                value=enemyteam,
            )
            embed.add_field(
                name='ACS',
                value="\n".join([self.__display_acs(p) for p in opponents]),
            )
            embed.add_field(name='KDA', value="\n".join([str(p.stats.kda) for p in opponents]))

            # page 2

        else:
            players = sorted(self.match.players, key=lambda p: p.stats.score, reverse=True)
            embed.add_field(
                name='Players',
                value='\n'.join([self.__display_player(player, p) for p in players]),
            )
            embed.add_field(name='SCORE', value='\n'.join([f'{p.stats.score}' for p in players]))
            embed.add_field(name='KDA', value='\n'.join([f'{p.stats.kda}' for p in players]))

        timelines = []

        for i, r in enumerate(self.match.round_results, start=1):
            if i == 12:
                timelines.append(' | ')

            timelines.append(r.emoji_by_player(player))

            if r.round_result_code == RoundResultCode.surrendered.value:
                break

        if match.match_info._game_mode_url not in [GameModeURL.escalation.value, GameModeURL.deathmatch.value]:
            if len(timelines) > 25:
                embed.add_field(name='Timeline:', value=''.join(timelines[:25]), inline=False)
                embed.add_field(name='Overtime:', value=''.join(timelines[25:]), inline=False)
            else:
                embed.add_field(name='Timeline:', value=''.join(timelines), inline=False)

        return embed

    def __build_page_2_d(
        self,
        match: MatchDetails,
        player: MatchPlayer,
        *,
        locale: discord.Locale,
    ) -> Embed:
        embed = self.__template_e(player, locale=locale)
        members = sorted(match.get_members(player), key=lambda p: p.stats.acs, reverse=True)
        opponents = sorted(match.get_opponents(player), key=lambda p: p.stats.acs, reverse=True)

        # MY TEAM
        embed.add_field(
            name='MY TEAM',
            value='\n'.join([self.__display_player(player, p) for p in members]),
        )
        embed.add_field(name='FK', value="\n".join([str(p.stats.first_kills) for p in members]))
        embed.add_field(
            name='HS%',
            value='\n'.join([(str(round(p.stats.head_shot_percent, 1)) + '%') for p in members]),
        )

        # ENEMY TEAM
        embed.add_field(
            name='ENEMY TEAM',
            value='\n'.join([self.__display_player(player, p, bold=False) for p in opponents]),
        )
        embed.add_field(name='FK', value='\n'.join([str(p.stats.first_kills) for p in opponents]))
        embed.add_field(
            name='HS%',
            value='\n'.join([(str(round(p.stats.head_shot_percent, 1)) + '%') for p in opponents]),
        )

        return embed

    def __build_page_3_d(
        self,
        player: MatchPlayer,
        *,
        locale: discord.Locale,
    ) -> Embed:
        embed = self.__template_e(player, performance=True, locale=locale)
        embed.add_field(
            name='KDA',
            value='\n'.join(
                [
                    p.kda
                    for p in sorted(
                        player.get_opponents_stats(),
                        key=lambda p: p.opponent.display_name.lower(),
                    )
                ]
            ),
        )
        embed.add_field(
            name='Opponent',
            value='\n'.join(
                self.__display_player(player, p.opponent)
                for p in sorted(
                    player.get_opponents_stats(),
                    key=lambda p: p.opponent.display_name.lower(),
                )
            ),
        )

        text = self.__display_abilities(player)
        if text != '':
            embed.add_field(name='Abilities', value=text, inline=False)

        return embed

    # def __build_death_match_d(
    #     self,
    #     match: MatchDetails,
    #     player: MatchPlayer,
    #     *,
    #     locale: valorantx.Locale,
    # ) -> Embed:
    #     embed = Embed()

    #     players = sorted(match.players, key=lambda p: p.stats.score, reverse=True)
    #     embed.set_author(
    #         name=match.match_info.game_mode.display_name.from_locale(locale)
    #         if match.match_info.game_mode is not None
    #         else None,
    #         icon_url=player.agent.display_icon if player.agent is not None else None,
    #     )
    #     embed.add_field(
    #         name='Players',
    #         value='\n'.join([self.__display_player(player, p) for p in players]),
    #     )
    #     embed.add_field(name='SCORE', value='\n'.join([f'{p.stats.score}' for p in players]))
    #     embed.add_field(name='KDA', value='\n'.join([f'{p.stats.kda}' for p in players]))
    #     return embed

    # mobile

    def __build_page_1_m(self, match: MatchDetails, player: MatchPlayer, *, locale: discord.Locale) -> Embed:
        embed = self.__template_e(player, locale=locale)

        members = sorted(match.get_members(player), key=lambda p: p.stats.acs, reverse=True)
        opponents = sorted(match.get_opponents(player), key=lambda p: p.stats.acs, reverse=True)

        if match.match_info._game_mode_url != GameModeURL.deathmatch.value:
            # MY TEAM
            embed.add_field(name='\u200b', value=chat.bold('MY TEAM'), inline=False)
            for p in members:
                embed.add_field(
                    name=self.__display_player(player, p),
                    value=f'ACS: {self.__display_acs(p)}\nKDA: {p.stats.kda}',
                    inline=True,
                )

            # ENEMY TEAM
            embed.add_field(name='\u200b', value=chat.bold('ENEMY TEAM'), inline=False)
            for p in opponents:
                embed.add_field(
                    name=self.__display_player(player, p),
                    value=f'ACS: {self.__display_acs(p)}\nKDA: {p.stats.kda}',
                    inline=True,
                )
        else:
            players = sorted(match.players, key=lambda p: p.stats.score, reverse=True)
            for p in players:
                embed.add_field(
                    name=self.__display_player(player, p),
                    value=f'SCORE: {p.stats.score}\nKDA: {p.stats.kda}',
                    inline=True,
                )

        timelines = []

        for i, r in enumerate(match.round_results, start=1):
            # if r.result_code == valorantx.RoundResultCode.surrendered:
            #     timelines.append('Surrendered')
            #     break

            if i == 12:
                timelines.append(' | ')

            timelines.append(r.emoji_by_player(player))

        if match.match_info._game_mode_url not in [GameModeURL.escalation.value, GameModeURL.deathmatch.value]:
            # TODO: __contains__ is not implemented for GameModeType
            if len(timelines) > 25:
                embed.add_field(name='Timeline:', value=''.join(timelines[:25]), inline=False)
                embed.add_field(name='Overtime:', value=''.join(timelines[25:]), inline=False)
            else:
                embed.add_field(name='Timeline:', value=''.join(timelines), inline=False)

        return embed

    def __build_page_2_m(self, match: MatchDetails, player: MatchPlayer, *, locale: discord.Locale) -> Embed:
        embed = self.__template_e(player, locale=locale)

        members = sorted(match.get_members(player), key=lambda p: p.stats.acs, reverse=True)
        opponents = sorted(match.get_opponents(player), key=lambda p: p.stats.acs, reverse=True)

        # MY TEAM
        embed.add_field(name='\u200b', value=chat.bold('MY TEAM'))
        for p in members:
            embed.add_field(
                name=self.__display_player(player, p),
                value=f'FK: {p.stats.first_kills}\nHS%: {round(p.stats.head_shot_percent, 1)}%',
                inline=True,
            )

        # ENEMY TEAM
        embed.add_field(name='\u200b', value=chat.bold('ENEMY TEAM'), inline=False)
        for p in opponents:
            embed.add_field(
                name=self.__display_player(player, p, bold=False),
                value=f'FK: {p.stats.first_kills}\nHS%: {round(p.stats.head_shot_percent, 1)}%',
                inline=True,
            )

        return embed

    def __build_page_3_m(self, player: MatchPlayer, *, locale: discord.Locale) -> Embed:
        embed = self.__template_e(player, performance=True, locale=locale)
        embed.add_field(
            name='KDA Opponent',
            value='\n'.join(
                [(p.kda + ' ' + self.__display_player(player, p.opponent)) for p in player.get_opponents_stats()]
            ),
        )

        text = self.__display_abilities(player)
        if text != '':
            embed.add_field(name='Abilities', value=text, inline=False)

        return embed

    # def __build_death_match_m(
    #     self,
    #     match: MatchDetails,
    #     player: MatchPlayer,
    #     *,
    #     locale: valorantx.Locale,
    # ) -> Embed:
    #     embed = Embed()

    #     players = sorted(match.players, key=lambda p: p.stats.score, reverse=True)
    #     embed.set_author(
    #         name=match.match_info.game_mode.display_name.from_locale(locale)
    #         if match.match_info.game_mode is not None
    #         else None,
    #         icon_url=player.agent.display_icon if player.agent is not None else None,
    #     )
    #     for p in players:
    #         embed.add_field(
    #             name=self.__display_player(player, p),
    #             value=f'SCORE: {p.stats.score}\nKDA: {p.stats.kda}',
    #             inline=True,
    #         )

    #     return embed

    # display

    def __display_player(self, player: MatchPlayer, other_player: MatchPlayer, *, bold: bool = True) -> str:
        def display_tier(player: MatchPlayer) -> str:
            tier = player.competitive_tier
            return (
                (' ' + tier.emoji + ' ')  # type: ignore
                if self.match.match_info.queue_id == 'competitive' and tier is not None
                else ''
            )

        text = (
            other_player.agent.emoji  # type: ignore
            + display_tier(other_player)
            + ' '
            + (chat.bold(other_player.display_name) if bold and other_player == player else other_player.display_name)
        )

        return text

    def __display_acs(self, player: MatchPlayer, star: bool = True) -> str:
        def display_mvp(player: MatchPlayer) -> str:
            if player == self.match.match_mvp:
                return '★'
            elif player == self.match.team_mvp:
                return '☆'
            return ''

        acs = str(int(player.stats.acs))
        if star:
            acs += ' ' + display_mvp(player)
        return acs

    def __display_abilities(self, player: MatchPlayer) -> str:
        abilities = player.stats.ability_casts
        if abilities is None:
            return ''

        return '{c_emoji} {c_casts} {q_emoji} {q_casts} {e_emoji} {e_casts} {x_emoji} {x_casts}'.format(
            c_emoji=abilities.c.emoji,  # type: ignore
            c_casts=round(abilities.c_casts / player.stats.rounds_played, 1),
            e_emoji=abilities.e.emoji,  # type: ignore
            e_casts=round(abilities.e_casts / player.stats.rounds_played, 1),
            q_emoji=abilities.q.emoji,  # type: ignore
            q_casts=round(abilities.q_casts / player.stats.rounds_played, 1),
            x_emoji=abilities.x.emoji,  # type: ignore
            x_casts=round(abilities.x_casts / player.stats.rounds_played, 1),
        )

    # build

    def build(
        self,
        puuid: str,
        *,
        locale: discord.Locale = discord.Locale.american_english,
    ) -> tuple[list[Embed], list[Embed]]:
        player = self.match.get_player(puuid)
        if player is None:
            raise ValueError(f'player {puuid} was not in this match')

        # desktop

        desktops = [
            self.__build_page_1_d(self.match, player, locale=locale),
            # self.__build_page_2_d(self.match, player, locale=locale),
            self.__build_page_3_d(player, locale=locale),
        ]

        # mobile

        mobiles = [
            self.__build_page_1_m(self.match, player, locale=locale),
            # self.__build_page_2_m(self.match, player, locale=locale),
            self.__build_page_3_m(player, locale=locale),
        ]

        # performance
        if self.match.match_info._game_mode_url != GameModeURL.deathmatch.value:
            desktops.insert(1, self.__build_page_2_d(self.match, player, locale=locale))
            mobiles.insert(1, self.__build_page_2_m(self.match, player, locale=locale))

        return desktops, mobiles


# class SelectMatchHistory(ui.Select['CarrierView']):
#     def __init__(self, *, options: list[discord.SelectOption], locale: discord.Locale) -> None:
#         super().__init__(
#             options=options or [discord.SelectOption(label=_('No Match History', locale), value='0')],
#             placeholder=_('Select Match to see details', locale),
#             row=1,
#             disabled=not options,
#         )
#         self.locale = locale

#     @classmethod
#     def from_match_history(
#         cls,
#         *,
#         match_history: MatchHistory,
#         locale: discord.Locale,
#     ) -> Self:
#         options = []
#         for match in match_history.match_details:
#             me = match.get_player(match_history.subject)
#             if me is None:
#                 continue

#             # find match score
#             left_team_score, right_team_score = find_match_score_by_player(match, me)  # type: ignore

#             # build option
#             option = discord.SelectOption(
#                 label=f'{left_team_score} - {right_team_score}',
#                 value=match.match_info.match_id,
#             )

#             # add emoji
#             if me.agent is not None:
#                 option.emoji = getattr(me.agent, 'emoji', None)

#             # add description
#             game_mode = match.match_info.game_mode
#             match_map = match.match_info.map
#             if match_map is not None and game_mode is not None:
#                 option.description = '{map} - {gamemode}'.format(
#                     map=match_map.display_name.from_locale(locale_converter.to_valorant(locale)),
#                     gamemode=game_mode.display_name.from_locale(locale_converter.to_valorant(locale)),
#                 )
#             options.append(option)
#         return cls(options=options, locale=discord.Locale.american_english)

#     def clear(self) -> None:
#         self.options.clear()

#     def add_dummy(self) -> None:
#         assert self.view is not None
#         self.clear()
#         self.add_option(label=_('No Match History', self.view.locale), value='0', emoji='📭')
#         self.disabled = True

#     async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
#         assert self.view is not None
#         # async with self.view.lock:
#         #     value = self.values[0]

#         #     await interaction.response.defer()

#         #     if self.puuid == '':
#         #         return

#         #     if value not in self._source:
#         #         return

#         #     # build source
#         #     source = MatchDetailsPageSource(self._source[value], self.puuid, locale_converter.to_valorant(self.view.locale))
#         #     self.match_details_view.source = source

#         #     # set message
#         #     if self.match_details_view.message is None and self.view.message is not None:
#         #         self.match_details_view.message = self.view.message

#         #     # start view
#         #     await self.match_details_view.start()


# class CarrierView(BaseView, LattePages):
#     def __init__(
#         self,
#         interaction: discord.Interaction[LatteMaid],
#         queue_id: str | None = None,
#     ) -> None:
#         super().__init__(interaction=interaction)
#         self.queue_id: str | None = queue_id
#         self.embeds: list[Embed] = []

#     def fill_items(self) -> None:
#         super().fill_items()
#         self.remove_item(self.stop_pages)
#         self.remove_item(self.numbered_page)

#     async def set_source(self) -> None:
#         assert self.account_manager is not None
#         assert self.current_puuid is not None
#         match_history = await self.valorant_client.fetch_match_history(
#             puuid=self.current_puuid,
#             queue=self.queue_id,
#             with_details=True,
#         )
#         self.add_item(
#             SelectMatchHistory.from_match_history(match_history=match_history, locale=self.locale),
#         )
#         self.source = CarrierPageSource(puuid=riot_auth.puuid, data=match_history.match_details)  # type: ignore

#     async def start_valorant(self) -> None:
#         await self.interaction.response.defer()
#         await self._init()
#         await self.set_source()
#         await self.start()


# class MatchDetailsPageSource(ListPageSource):
#     def __init__(self, match_details: MatchDetails, puuid: str, locale: discord.Locale) -> None:
#         self.puuid = puuid
#         self.locale = locale
#         self.match_embed = e.MatchDetailsEmbed(match_details)  # type: ignore
#         super().__init__(self.build_entries(locale), per_page=1)

#     def build_entries(self, locale: discord.Locale) -> list[tuple[Embed, Embed]]:
#         entries = []
#         try:
#             desktops, mobiles = self.match_embed.build(self.puuid, locale=locale_converter.to_valorant(locale))
#         except Exception as exc:
#             _log.error(f'failed to build match details embed for {self.puuid}', exc_info=exc)
#         else:
#             for dt, mb in zip(desktops, mobiles):
#                 entries.append((dt, mb))
#         return entries

#     def format_page(self, menu: MatchDetailsView, entries: tuple[Embed, Embed]) -> Embed:
#         desktops, mobiles = entries

#         # locale changed
#         if menu.locale != self.locale:
#             self.locale = menu.locale
#             self.entries = self.build_entries(self.locale)
#             desktops, mobiles = self.entries[menu.current_page]

#         return mobiles if menu.is_on_mobile() else desktops


# class MatchDetailsView(ViewAuthor, LattePages):
#     __view_on_mobile__: bool = False

#     def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
#         super().__init__(interaction)
#         self.compact = True
#         # self.source = source
#         # self.carrier_view: Optional[CarrierView] = carrier_view
#         # self.valorant_locale: ValorantLocale = locale_converter.to_valorant(interaction.locale)
#         # self.back_to_home.label = _('Back', self.locale)

#     def fill_items(self) -> None:
#         # if self.carrier_view is not None:
#         #     self.add_item(self.back_to_home)
#         super().fill_items()
#         self.remove_item(self.go_to_last_page)
#         self.remove_item(self.go_to_first_page)
#         self.remove_item(self.stop_pages)
#         self.go_to_next_page.label = self.go_to_last_page.label
#         self.go_to_previous_page.label = self.go_to_first_page.label
#         # self.add_item(self.toggle_ui)

#     def is_on_mobile(self) -> bool:
#         return self.__view_on_mobile__

#     # @ui.button(emoji='📱', style=ButtonStyle.green)
#     # async def toggle_ui(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
#     #     button.emoji = '📱' if self.is_on_mobile() else '💻'
#     #     self.__view_on_mobile__ = not self.is_on_mobile()
#     #     await self.show_checked_page(interaction, self.current_page)

#     # @ui.button(label=_('Back'), style=ButtonStyle.gray, custom_id='home_button')
#     # async def back_to_home(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
#     #     # assert self.carrier_view is not None
#     #     await interaction.response.defer()

#     #     if self.carrier_view is None:
#     #         return

#     #     if self.message is None:
#     #         return

#     #     self.carrier_view.reset_timeout()

#     #     await self.safe_edit_message(self.message, embeds=self.carrier_view.embeds, view=self.carrier_view)
