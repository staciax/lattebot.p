from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeVar

import discord
from discord import Interaction, app_commands
from discord.app_commands.checks import (
    Cooldown as Cooldown,
    bot_has_permissions as bot_has_permissions,
    cooldown as cooldown,
    dynamic_cooldown as dynamic_cooldown,
    has_any_role as has_any_role,
    has_permissions as has_permissions,
    has_role as has_role,
)

if TYPE_CHECKING:
    from .bot import LatteMaid

__all__ = (
    'owner_only',
    'Cooldown',
    'bot_has_permissions',
    'cooldown',
    'dynamic_cooldown',
    'has_any_role',
    'has_permissions',
    'has_role',
    'cooldown_short',
    'cooldown_medium',
    'cooldown_long',
    'custom_cooldown',
)
T = TypeVar('T')


def owner_only() -> Callable[[T], T]:
    async def actual_check(interaction: Interaction[LatteMaid]):
        return await interaction.client.is_owner(interaction.user)

    return app_commands.check(actual_check)


def cooldown_short(interaction: discord.Interaction[LatteMaid]) -> Cooldown | None:
    if interaction.user == interaction.client.owner:
        return None
    return Cooldown(1, 5)


def cooldown_medium(interaction: discord.Interaction[LatteMaid]) -> Cooldown | None:
    if interaction.user == interaction.client.owner:
        return None
    return Cooldown(1, 10)


def cooldown_long(interaction: discord.Interaction[LatteMaid]) -> Cooldown | None:
    if interaction.user == interaction.client.owner:
        return None
    return Cooldown(1, 20)


def custom_cooldown(interaction: discord.Interaction[LatteMaid], rate: float, per: float) -> Cooldown | None:
    if interaction.user == interaction.client.owner:
        return None
    return Cooldown(rate, per)
