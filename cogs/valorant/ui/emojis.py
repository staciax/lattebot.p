from enum import Enum


class Point(str, Enum):
    valorant = '<:currency_valorant:1042817047953952849>'
    radianite = '<:currency_radianite:1042817896398737417>'

    def __str__(self) -> str:
        return self.value
