import os
from typing import Iterable

# fmt: off
__all__ = (
    'count_python',
)
# fmt: on


# - thanks for stella_bot: https://github.com/InterStella0/stella_bot


def reading_recursive(root: str, /) -> Iterable[int]:
    if root.startswith('./venv'):
        return
    for x in os.listdir(root):
        if os.path.isdir(x):
            yield from reading_recursive(root + '/' + x)
            for y in os.listdir(root + '/' + x):
                if os.path.isdir(root + '/' + x + '/' + y):
                    yield from reading_recursive(root + '/' + x + '/' + y)
        else:
            if x.endswith('.py') and not root.startswith('./_'):
                with open(f'{root}/{x}', encoding='utf-8') as r:
                    yield len(r.readlines())


def count_python(root: str) -> int:
    return sum(reading_recursive(root))
