from __future__ import annotations

from typing import TYPE_CHECKING

from .help import Help

if TYPE_CHECKING:
    from core.bot import LatteMaid


async def setup(bot: LatteMaid) -> None:
    await bot.add_cog(Help(bot))
