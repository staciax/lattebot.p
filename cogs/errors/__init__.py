from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import Errors

if TYPE_CHECKING:
    from core.bot import LatteMaid


async def setup(bot: LatteMaid) -> None:
    await bot.add_cog(Errors(bot))
