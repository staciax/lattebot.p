from __future__ import annotations

from core.i18n import I18n

from .abc import MixinMeta

SUPPORT_GUILD_ID = 1097859504906965042

_ = I18n('valorant.admin', __file__, read_only=True)


class Admin(MixinMeta):
    ...
