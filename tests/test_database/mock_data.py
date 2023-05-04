import datetime

USER_DATA = [
    {
        'id': 1,
        'locale': 'en_US',
    },
    {
        'id': 2,
        'locale': 'en_GB',
    },
    {
        'id': 3,
        'locale': 'th_TH',
    },
]

BLACKLIST_DATA = [
    {
        'id': 1,
        'reason': 'test',
    },
    {
        'id': 2,
        'reason': 'test',
    },
    {
        'id': 3,
        'reason': 'test',
    },
]

COMMAND_DATA = [
    {
        'guild': 1,
        'channel': 1,
        'author': 1,
        'used': datetime.datetime.utcnow(),
        'prefix': '/',
        'command': 'test 1',
        'failed': False,
        'app_command': True,
    },
    {
        'guild': 2,
        'channel': 2,
        'author': 2,
        'used': datetime.datetime.utcnow(),
        'prefix': '/',
        'command': 'test 2',
        'failed': False,
        'app_command': True,
    },
    {
        'guild': 3,
        'channel': 3,
        'author': 3,
        'used': datetime.datetime.utcnow(),
        'prefix': '/',
        'command': 'test 3',
        'failed': True,
        'app_command': True,
    },
]
