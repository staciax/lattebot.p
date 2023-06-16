__all__ = (
    'DatabaseBaseError',
    'UserAlreadyExists',
    'UserDoesNotExist',
    'BlacklistAlreadyExists',
    'BlacklistDoesNotExist',
    'RiotAccountAlreadyExists',
    'RiotAccountDoesNotExist',
)


class DatabaseBaseError(Exception):
    """Base class for all database errors."""


class UserAlreadyExists(DatabaseBaseError):
    """Raised when a user already exists in the database."""

    def __init__(self, user_id: int, /) -> None:
        self.user_id = user_id
        super().__init__(f'User with id {id} already exists in the database.')


class UserDoesNotExist(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    def __init__(self, user_id: int, /) -> None:
        self.user_id = user_id
        super().__init__(f'User with id {id} does not exist in the database.')


class BlacklistAlreadyExists(DatabaseBaseError):
    """Raised when a user already exists in the database."""

    def __init__(self, user_id: int, /) -> None:
        self.user_id = id
        super().__init__(f'User with id {id} already exists in the database.')


class BlacklistDoesNotExist(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    def __init__(self, user_id: int, /) -> None:
        self.user_id = user_id
        super().__init__(f'User with id {id} does not exist in the database.')


class RiotAccountDoesNotExist(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    def __init__(self, puuid: str, owner_id: int, /) -> None:
        self.puuid = puuid
        self.owner_id = owner_id
        super().__init__(f'Riot account with puuid {puuid} and owner id {owner_id} does not exist in the database.')


class RiotAccountAlreadyExists(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    def __init__(self, puuid: str, owner_id: int, /) -> None:
        self.puuid = puuid
        self.owner_id = owner_id
        super().__init__(f'Riot account with puuid {puuid} and owner id {owner_id} already exists in the database.')
