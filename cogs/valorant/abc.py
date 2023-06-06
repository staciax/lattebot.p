from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import valorantx2 as valorantx

    from core.bot import LatteMaid


class MixinMeta(ABC):
    """Metaclass for mixin classes."""

    if TYPE_CHECKING:
        bot: LatteMaid
        valorant_client: valorantx.Client

    def __init__(self, *_args):
        pass
