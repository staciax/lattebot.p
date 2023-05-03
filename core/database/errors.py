__all__ = (
    'DatabaseBaseError',
    'UserAlreadyExists',
    'UserDoesNotExist',
    'BlacklistAlreadyExists',
    'BlacklistDoesNotExist',
)


class DatabaseBaseError(Exception):
    """Base class for all database errors."""

    pass


class UserAlreadyExists(DatabaseBaseError):
    """Raised when a user already exists in the database."""

    pass


class UserDoesNotExist(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    pass


class BlacklistAlreadyExists(DatabaseBaseError):
    """Raised when a user already exists in the database."""

    pass


class BlacklistDoesNotExist(DatabaseBaseError):
    """Raised when a user does not exist in the database."""

    pass
