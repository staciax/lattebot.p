from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .main import Valorant

_log = logging.getLogger(__name__)

skip = False
try:
    import bs4  # type: ignore
    import lxml  # type: ignore
except ImportError:
    skip = True
    _log.warning(
        "bs4 and lxml are not installed. Please install them with `pip3 install -r cogs/valorant/requirements.txt`."
    )

if TYPE_CHECKING:
    from core.bot import LatteMaid


async def setup(bot: LatteMaid) -> None:
    if not skip:
        await bot.add_cog(Valorant(bot))
        return
