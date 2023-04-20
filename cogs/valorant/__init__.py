from __future__ import annotations

from typing import TYPE_CHECKING

from .main import Valorant

try:
    import bs4  # type: ignore
    import lxml  # type: ignore
except ImportError:
    raise RuntimeError(
        "bs4 and lxml are not installed. Please install them with `pip3 install -r cogs/valorant/requirements.txt`."
    )


if TYPE_CHECKING:
    from core.bot import LatteMaid


async def setup(bot: LatteMaid) -> None:
    await bot.add_cog(Valorant(bot))
