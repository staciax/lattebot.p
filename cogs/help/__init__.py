from __future__ import annotations

from typing import TYPE_CHECKING

from .help import Help

if TYPE_CHECKING:
    from core.bot import LatteMiad


async def setup(bot: LatteMiad) -> None:
    await bot.add_cog(Help(bot))
