from typing import Any, Optional, Union

import discord
from discord.app_commands import AppCommandError as DiscordAppCommandError
from discord.app_commands.commands import Command, ContextMenu
from discord.app_commands.models import AppCommand, AppCommandGroup

# TODO: improve this


class LatteMaidError(DiscordAppCommandError):
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


class ValorantExtError(LatteMaidError):
    """Base class for all valorant cog errors."""

    def __init__(self, message: Optional[str] = None, /) -> None:
        self.message = message
        super().__init__(message)


class RiotAuthError(ValorantExtError):
    """Base class for all valorant cog Riot auth errors."""

    pass


class RiotAuthNotLinked(RiotAuthError):
    """Raised when a user does not have a Riot account linked."""

    pass


class RiotAuthAlreadyLinked(RiotAuthError):
    """Raised when a user already has a Riot account linked."""

    pass


class RiotAuthMaxLimitReached(RiotAuthError):
    """Raised when a user has reached the max limit of Riot accounts."""

    pass


class RiotAuthMultiFactorTimeout(RiotAuthError):
    """Raised when a user has reached the max limit of Riot accounts."""

    pass


# class BadArgument(LatteMaidError):
#     """Raised when a command is called with invalid arguments."""

#     pass


# class CommandNotFound(LatteMaidError):
#     """Raised when a command is not found."""

#     pass


# class CheckFailure(LatteMaidError):
#     """Raised when a check fails."""

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
        command: Optional[Union[Command[Any, ..., Any], ContextMenu, AppCommand, AppCommandGroup]],
        author: Optional[Union[discord.User, discord.Member]],
    ) -> None:
        self.command: Optional[Union[Command[Any, ..., Any], ContextMenu, AppCommand, AppCommandGroup]] = command
        self.author: Optional[Union[discord.User, discord.Member]] = author
        message = f'You are not allowed to use this.'
        fmt = 'Only {author} can use this command. If you want to use it, use {command}'
        if isinstance(command, (Command, ContextMenu)) and author is not None:
            message = fmt.format(author=author.mention, command=command.qualified_name)
        elif isinstance(command, (AppCommand, AppCommandGroup)) and author is not None:
            message = fmt.format(author=author.mention, command=command.mention)
        self.message = message
        super().__init__(message)
