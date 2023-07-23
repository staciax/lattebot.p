from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import valorantx2 as valorantx
    from core.bot import LatteMiad


class MixinMeta(ABC):
    """Metaclass for mixin classes."""

    if TYPE_CHECKING:
        bot: LatteMiad

        @property
        def valorant_client(self) -> valorantx.Client:
            ...

    def __init__(self, *_args):
        pass
