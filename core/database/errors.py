__all__ = (
    'DatabaseBaseError',
    'UserAlreadyExists',
    'UserDoesNotExist',
    'BlacklistAlreadyExists',
    'BlacklistDoesNotExist',
    'RiotAccountAlreadyExists',
    'RiotAccountDoesNotExist',
    'NotificationAlreadyExists',
    'NotificationDoesNotExist',
    'NotificationSettingsAlreadyExists',
    'NotificationSettingsDoesNotExist',
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


class NotificationDoesNotExist(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    def __init__(self, owner_id: int, item_id: str, /) -> None:
        self.owner_id = owner_id
        self.item_id = item_id
        super().__init__(f'Notification with item id {item_id} and owner id {owner_id} does not exist in the database.')


class NotificationAlreadyExists(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    def __init__(self, owner_id: int, item_id: str, /) -> None:
        self.owner_id = owner_id
        self.item_id = item_id
        super().__init__(f'Notification with item id {item_id} and owner id {owner_id} already exists in the database.')


class NotificationSettingsDoesNotExist(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    def __init__(self, owner_id: int, /) -> None:
        self.owner_id = owner_id
        super().__init__(f'Notification settings with owner id {owner_id} does not exist in the database.')


class NotificationSettingsAlreadyExists(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    def __init__(self, owner_id: int, /) -> None:
        self.owner_id = owner_id
        super().__init__(f'Notification settings with owner id {owner_id} already exists in the database.')
