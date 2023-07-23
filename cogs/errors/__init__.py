from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import Errors

if TYPE_CHECKING:
    from core.bot import LatteMiad


async def setup(bot: LatteMiad) -> None:
    await bot.add_cog(Errors(bot))
