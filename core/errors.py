from typing import Any

import discord
from discord.app_commands.commands import Command, ContextMenu
from discord.app_commands.models import AppCommand, AppCommandGroup

# TODO: improve this


class LatteMaidError(Exception):
    """Base class for all Latte errors."""

    # def __init__(
    #     self,
    #     message: Optional[str] = None,
    #     # view: Optional[View] = None,
    #     # modal: Optional[Modal] = None,
    #     # ephemeral: bool = True,
    #     # delete_after: Optional[float] = None,
    #     # *args: Any,
    #     # **kwargs: Any,
    # ) -> None:
    #     super().__init__(message, *args)
    #     # self.message: Optional[str] = message
    #     # self.view: Optional[View] = view
    #     # self.modal: Optional[Modal] = modal
    #     # self.ephemeral: bool = ephemeral
    #     # self.delete_after: Optional[float] = delete_after
    #     # self.extras: Dict[Any, Any] = kwargs


class AppCommandError(LatteMaidError):
    """Base class for all lattemaid app command errors."""

    pass


class UserInputError(AppCommandError):
    """Base class for errors that involve errors regarding user input."""

    def __init__(self, message: str) -> None:
        self.message: str = message
        super().__init__(message)


class MissingRequiredArgument(UserInputError):
    def __init__(self, param: str) -> None:
        self.param: str = param
        super().__init__(f'{param} is a required argument that is missing.')


class BadArgument(UserInputError):
    """Raised when a bad argument is passed to a command."""

    pass


# class CommandNotFound(LatteMaidError):
#     """Raised when a command is not found."""

#     pass


# class CommandInvokeError(LatteMaidError):
#     """Raised when a command invoke fails."""

#     pass


# class CommandOnCooldown(LatteMaidError):
#     """Raised when a command is on cooldown."""

#     pass


# class UserNotFound(LatteMaidError):
#     """Raised when a user is not found."""

#     pass


# class NotOwner(LatteMaidError):
#     """Raised when a user is not found."""

#     pass


class ComponentOnCooldown(LatteMaidError):
    """Raised when a component is on cooldown."""

    def __init__(
        self,
        cooldown: discord.app_commands.Cooldown,
        retry_after: float,
    ) -> None:
        self.cooldown: discord.app_commands.Cooldown = cooldown
        self.retry_after: float = retry_after
        super().__init__(f'You are on cooldown. Try again in {self.retry_after:.2f}s')


class CheckFailure(LatteMaidError):
    """Raised when a check fails."""

    def __init__(
        self,
        command: Command[Any, ..., Any] | ContextMenu | AppCommand | AppCommandGroup | None,
        author: discord.User | discord.Member | None,
    ) -> None:
        self.command: Command[Any, ..., Any] | ContextMenu | AppCommand | AppCommandGroup | None = command
        self.author: discord.User | discord.Member | None = author
        super().__init__('You are not allowed to use this.')
