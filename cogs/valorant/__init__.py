from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .main import Valorant

_log = logging.getLogger(__name__)

try:
    import bs4  # type: ignore
    import lxml  # type: ignore
except ImportError:
    skip = True
    _log.warning(
        "bs4 and lxml are not installed. Please install them with `pip3 install -r cogs/valorant/requirements.txt`."
    )
else:
    skip = False
    del bs4, lxml

if TYPE_CHECKING:
    from core.bot import LatteMiad


async def setup(bot: LatteMiad) -> None:
    if not skip:
        await bot.add_cog(Valorant(bot))
        return
