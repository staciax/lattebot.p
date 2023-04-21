from __future__ import annotations

# from functools import cached_property
from typing import TYPE_CHECKING, List

from valorantx2.valorant_api import Localization
from valorantx2.valorant_api.models import (
    Ability as ValorantAPIAbility,
    Agent as ValorantAPIAgent,
    CompetitiveTier as ValorantAPICompetitiveTier,
    ContentTier as ValorantAPIContentTier,
    Currency as ValorantAPICurrency,
    GameMode as ValorantAPIGameMode,
    Tier as ValorantAPITier,
)

from ..emojis import (
    get_ability_emoji,
    get_agent_emoji,
    get_content_tier_emoji,
    get_currency_emoji,
    get_game_mode_emoji,
    get_tier_emoji,
)

if TYPE_CHECKING:
    from valorantx2.valorant_api.types.agents import Agent as AgentPayload
    from valorantx2.valorant_api.types.competitive_tiers import CompetitiveTier as CompetitiveTierPayload
    from valorantx2.valorant_api.types.gamemodes import GameMode as GameModePayload

    from ..valorant_api_cache import Cache

__all__ = (
    'Agent',
    'Tier',
    'ContentTier',
    'CompetitiveTier',
    'Currency',
    'GameMode',
)

# agents


class Ability(ValorantAPIAbility):
    @property
    def emoji(self) -> str:
        key = (
            (self.agent.display_name.default.lower() + '_' + self.display_name.default.lower())
            .replace('/', '_')
            .replace(' ', '_')
            .replace('___', '_')
            .replace('__', '_')
            .replace("'", '')
        )
        return get_ability_emoji(key)


class Agent(ValorantAPIAgent):
    def __init__(self, *, state: Cache, data: AgentPayload) -> None:
        super().__init__(state=state, data=data)
        self._abilities: List[Ability] = [
            Ability(state=state, data=ability, agent=self) for ability in data['abilities']
        ]

    @property
    def emoji(self) -> str:
        return get_agent_emoji(self.display_name.default)


# competitive tiers


class Tier(ValorantAPITier):
    @property
    def emoji(self) -> str:
        # will not be used as a tier number because each season's rank is different
        return get_tier_emoji(self.display_name.default)


class CompetitiveTier(ValorantAPICompetitiveTier):
    def __init__(self, state: Cache, data: CompetitiveTierPayload) -> None:
        super().__init__(state, data)
        self._tiers: List[Tier] = [Tier(state=self._state, data=tier) for tier in data['tiers']]


# content tiers


class ContentTier(ValorantAPIContentTier):
    @property
    def emoji(self) -> str:
        return get_content_tier_emoji(self.dev_name)


# currencies


class Currency(ValorantAPICurrency):
    @property
    def emoji(self) -> str:
        return get_currency_emoji(self.uuid)


# game modes


class GameMode(ValorantAPIGameMode):
    def __init__(self, state: Cache, data: GameModePayload, *, is_ranked: bool = False) -> None:
        super().__init__(state=state, data=data)
        self.__display_name_override(is_ranked)

    @property
    def emoji(self) -> str:
        # return get_game_mode_emoji(self.uuid)
        return get_game_mode_emoji(self.display_name.default)

    def __display_name_override(self, is_ranked: bool) -> None:
        # TODO: swiftplay ?
        if self.uuid == '96bd3920-4f36-d026-2b28-c683eb0bcac5':
            if is_ranked:
                self._display_name = {
                    "ar-AE": "تنافسي",
                    "de-DE": "Gewertet",
                    "en-US": "Competitive",
                    "es-ES": "Competitivo",
                    "es-MX": "Competitivo",
                    "fr-FR": "Compétition",
                    "id-ID": "Competitive",
                    "it-IT": "Competitiva",
                    "ja-JP": "コンペティティブ",
                    "ko-KR": "경쟁전",
                    "pl-PL": "Rankingowa",
                    "pt-BR": "Competitivo",
                    "ru-RU": "рейтинговaя игра",
                    "th-TH": "Competitive",
                    "tr-TR": "Rekabete dayalı",
                    "vi-VN": "thi đấu xếp hạng",
                    "zh-CN": "競技模式",
                    "zh-TW": "競技模式",
                }
            else:
                self._display_name = {
                    "ar-AE": "غير مصنف",
                    "de-DE": "Ungewertet",
                    "en-US": "Unrated",
                    "es-ES": "No competitivo",
                    "es-MX": "Normal",
                    "fr-FR": "Non classé",
                    "id-ID": "Unrated",
                    "it-IT": "Non competitiva",
                    "ja-JP": "アンレート",
                    "ko-KR": "일반전",
                    "pl-PL": "Nierankingowa",
                    "pt-BR": "Sem classificação",
                    "ru-RU": "БЕЗ Рaнгa",
                    "th-TH": "Unrated",
                    "tr-TR": "Derecesiz",
                    "vi-VN": "Đấu Thường",
                    "zh-CN": "一般模式",
                    "zh-TW": "一般模式",
                }
            self._display_name_localized = Localization(self._display_name, locale=self._state.locale)
