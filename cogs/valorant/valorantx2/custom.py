from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Tuple, TypedDict, Union
from uuid import UUID

import valorantx
from valorantx import CurrencyType, GameModeType, Localization
from valorantx.models import match

from .enums import AbilitiesEmoji, AgentEmoji, ContentTierEmoji, GameModeEmoji, PointEmoji, RoundResultEmoji, TierEmoji

if TYPE_CHECKING:
    from typing_extensions import Self

    from .client import Client

__all__: Tuple[str, ...] = (
    'Ability',
    'Agent',
    'Currency',
    'Tier',
    'CompetitiveTier',
    'ContentTier',
    'MatchRoundResult',
    'GameMode',
    'MatchDetails',
    'MatchDetails',
    'PartialAccount',
    'Player',
)


class Ability(valorantx.AgentAbility):
    def __init__(self, client: Client, data: Dict[str, Any], agent: Optional[valorantx.Agent] = None) -> None:
        super().__init__(client, data)
        self.emoji_key: str = '' if agent is None else self.__build_emoji_key(agent.display_name.default)

    def __build_emoji_key(self, value: str) -> str:
        return (
            (value.lower() + '_' + self.display_name.default.lower())
            .replace('/', '_')
            .replace(' ', '_')
            .replace('___', '_')
            .replace('__', '_')
            .replace("'", '')
        )

    @property
    def emoji(self) -> str:
        return AbilitiesEmoji.get(self.emoji_key)


class Agent(valorantx.Agent):
    @property
    def abilities(self) -> List[Ability]:
        # TODO: remove this property in the next version
        return self.get_abilities()

    def get_abilities(self) -> List[Ability]:
        """:class: `List[AgentAbility]` Returns the agent's abilities."""
        return [Ability(client=self._client, data=ability, agent=self) for ability in self._abilities]

    @property
    def emoji(self) -> str:
        return AgentEmoji.get(self.display_name.default)


class Currency(valorantx.Currency):
    @property
    def emoji(self) -> str:
        return str(PointEmoji.valorant) if self.uuid == str(CurrencyType.valorant) else str(PointEmoji.radianite)


class Tier(valorantx.Tier):
    @property
    def emoji(self) -> str:
        # will not be used as a tier number because each season's rank is different
        return TierEmoji.get(self.display_name.default)


class CompetitiveTier(valorantx.CompetitiveTier):
    def get_tiers(self) -> List[Tier]:
        """:class: `list` Returns the competitive tier's tiers."""
        return [Tier(client=self._client, data=tier) for tier in self._tiers]


class ContentTier(valorantx.ContentTier):
    @property
    def emoji(self) -> str:
        return ContentTierEmoji.get(self.dev_name)


class MatchRoundResult(match.RoundResult):
    @property
    def emoji(self) -> str:
        return RoundResultEmoji.get(str(self.result_code), self.winning_team() == self.match.me.team)

    def emoji_by_player(self, player: valorantx.MatchPlayer) -> str:
        return RoundResultEmoji.get(str(self.result_code), self.winning_team() == player.team)


class GameMode(valorantx.GameMode):
    def __init__(self, client: Client, data: Mapping[str, Any], **kwargs) -> None:
        super().__init__(client=client, data=data)
        self._display_name: Union[str, Dict[str, str]] = data['displayName']
        self._is_ranked: bool = kwargs.get('is_ranked', False)
        self.__display_name_override()

    @property
    def emoji(self) -> str:
        return GameModeEmoji.get(self.display_name.default)

    def is_ranked(self) -> bool:
        """:class: `bool` Returns whether the game mode is ranked."""
        return self._is_ranked

    def __display_name_override(self) -> None:
        if self.uuid == '96bd3920-4f36-d026-2b28-c683eb0bcac5':
            if self._is_ranked:
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
            self._display_name_localized = Localization(self._display_name, locale=self._client.locale)


class MatchDetails(valorantx.MatchDetails):
    def __init__(self, client: Client, data: Any) -> None:
        super().__init__(client=client, data=data)
        self._round_results: List[MatchRoundResult] = (
            [MatchRoundResult(self, data) for data in data['roundResults']] if data.get('roundResults') else []
        )

    @property
    def game_mode(self) -> Optional[GameMode]:
        """:class:`GameMode`: The game mode this match was played in."""
        return self._client.get_game_mode(uuid=GameModeType.from_url(self._game_mode), is_ranked=self._is_ranked)


class AccountPlayerCardPayload(TypedDict):
    small: str
    large: str
    wide: str
    id: str


class AccountPayload(TypedDict):
    puuid: str
    region: str
    account_level: int
    name: str
    tag: str
    card: AccountPlayerCardPayload
    last_update: str
    last_update_raw: int


class PartialAccount:
    if TYPE_CHECKING:
        _client: Client
        puuid: UUID
        region: str
        account_level: int
        name: str
        tag: str
        player_card: Optional[valorantx.PlayerCard]
        _last_update: str
        _last_update_raw: int

    def __init__(self, client: Client, data: AccountPayload) -> None:
        self._client: Client = client
        self.player_card: Optional[valorantx.PlayerCard] = None
        self._update(data)

    def __repr__(self) -> str:
        return f'<PartialAccount puuid={self.puuid!r} name={self.name!r} tag={self.tag!r}>'

    @property
    def display_name(self) -> str:
        """:class:`str`: The account's display name."""
        return f'{self.name}#{self.tag}'

    @property
    def last_update(self) -> datetime:
        """:class:`datetime.datetime`: The last time the account was updated."""
        return datetime.fromtimestamp(self._last_update_raw / 1000)

    def _update(self, data: AccountPayload) -> None:
        self.puuid: UUID = UUID(data['puuid'])
        self.region: str = data['region']
        self.account_level: int = data['account_level']
        self.name: str = data['name']
        self.tag: str = data['tag']
        self.player_card = self._client.get_player_card(data['card']['id'])
        self._last_update: str = data['last_update']
        self._last_update_raw: int = data['last_update_raw']


class Player(valorantx.Player):
    @classmethod
    def from_partial_account(cls, client: Client, account: PartialAccount) -> Self:
        payload = {
            'puuid': str(account.puuid),
            'username': account.name,
            'tagline': account.tag,
            'region': account.region,
        }
        return cls(client=client, data=payload)
