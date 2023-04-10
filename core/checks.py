from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

import discord
from discord import Interaction, app_commands

if TYPE_CHECKING:
    from .bot import LatteMaid

__all__: Tuple[str, ...] = (
    'owner_only',
    'cooldown_5s',
    'cooldown_10s',
    'custom_cooldown',
)


def owner_only() -> app_commands.check:
    async def actual_check(interaction: Interaction[LatteMaid]):
        return await interaction.client.is_owner(interaction.user)

    return app_commands.check(actual_check)


def cooldown_5s(interaction: discord.Interaction[LatteMaid]) -> Optional[app_commands.Cooldown]:
    if interaction.user == interaction.client.owner:
        return None
    return app_commands.Cooldown(1, 5)


def cooldown_10s(interaction: discord.Interaction[LatteMaid]) -> Optional[app_commands.Cooldown]:
    if interaction.user == interaction.client.owner:
        return None
    return app_commands.Cooldown(1, 10)


def custom_cooldown(
    interaction: discord.Interaction[LatteMaid], rate: float, per: float
) -> Optional[app_commands.Cooldown]:
    if interaction.user == interaction.client.owner:
        return None
    return app_commands.Cooldown(rate, per)
