import logging

import yarl
from valorantx import RiotAuth as RiotAuth_

# fmt: off
__all__ = (
    'RiotAuth',
)
# fmt: on

_log = logging.getLogger(__name__)


# https://github.com/floxay/python-riot-auth


class RiotAuth(RiotAuth_):
    def get_ssid(self) -> str:
        url = yarl.URL('https://auth.riotgames.com')
        riot_cookies = self._cookie_jar.filter_cookies(url)
        if 'ssid' not in riot_cookies:
            return ''
        return riot_cookies['ssid'].value
