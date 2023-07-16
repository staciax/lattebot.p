import datetime

USER_DATA = [
    {
        'id': 1,
    },
    {
        'id': 2,
    },
    {
        'id': 3,
    },
]

BLACKLIST_DATA = [
    {
        'object_id': 1,
        'reason': 'test',
    },
    {
        'object_id': 2,
        'reason': 'test',
    },
    {
        'object_id': 3,
        'reason': 'test',
    },
]

APP_COMMAND_DATA = [
    {
        'type': 1,
        'guild': 1,
        'channel': 1,
        'author': 1,
        'used': datetime.datetime.utcnow(),
        'command': 'test 1',
        'failed': False,
    },
    {
        'type': 2,
        'guild': 2,
        'channel': 2,
        'author': 2,
        'used': datetime.datetime.utcnow(),
        'command': 'test 2',
        'failed': False,
    },
    {
        'type': 3,
        'guild': 3,
        'channel': 3,
        'author': 3,
        'used': datetime.datetime.utcnow(),
        'command': 'test 3',
        'failed': True,
    },
]
