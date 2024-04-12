from typing import NotRequired, TypedDict


class AccountPlayerCard(TypedDict):
    small: str
    large: str
    wide: str
    id: str


class Account(TypedDict):
    puuid: str
    region: str
    account_level: int
    name: str
    tag: str
    card: AccountPlayerCard
    last_update: str
    last_update_raw: int


class Error(TypedDict):
    message: int
    details: str


class Response(TypedDict):
    status: int
    data: Account
    errors: NotRequired[list[Error]]
