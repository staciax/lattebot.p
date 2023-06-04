from __future__ import annotations

from typing import TYPE_CHECKING

from core.cog import LatteMaidCog

if TYPE_CHECKING:
    import valorantx2 as valorantx

    from core.bot import LatteMaid


class ValorantCog(LatteMaidCog):
    def __init__(self, *_args):
        v_client: valorantx.Client
        bot: LatteMaid
