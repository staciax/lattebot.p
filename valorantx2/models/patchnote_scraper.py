from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, FeatureNotFound
from valorantx.valorant_api import Asset

# fmt: off
__all__ = (
    'PatchNoteScraper',
)
# fmt: on

if TYPE_CHECKING:
    from typing_extensions import Self

    from ..client import Client


class PatchNoteScraper:
    def __init__(self, client: Client, title: str | None, banner_url: str | None) -> None:
        self._client: Client = client
        self._title: str | None = title
        self._banner_url: str | None = banner_url

    def __repr__(self) -> str:
        return f'<PatchNote title={self.title!r}> banner={self.banner!r}>'

    @property
    def title(self) -> str | None:
        return self._title

    @property
    def banner(self) -> Asset | None:
        if self._banner_url is None:
            return None
        return Asset._from_url(self._client.valorant_api.cache, self._banner_url)

    @staticmethod
    def __to_soup(text: str) -> BeautifulSoup:
        # lxml is faster than html.parser
        try:
            # try to use lxml
            soup = BeautifulSoup(text, 'lxml')
        except FeatureNotFound:
            # fallback to html.parser
            soup = BeautifulSoup(text, 'html.parser')
        return soup

    @staticmethod
    def __get_title(soup: BeautifulSoup) -> str | None:
        soup_title = soup.find('title')
        if soup_title is not None:
            return soup_title.text
        return None

    @staticmethod
    def __get_banner_url(soup: BeautifulSoup) -> str | None:
        banners = soup.find_all('img')
        for banner in banners:
            if 'src' in banner.attrs:
                if 'Highlights' in banner['src']:
                    return banner['src']
        return None

    @classmethod
    async def fetch_from_url(cls, client: Client, url: str) -> Self:
        text = await client.http.text_from_url(url)
        soup = cls.__to_soup(text)
        title = cls.__get_title(soup)
        banner_url = cls.__get_banner_url(soup)
        return cls(client, title, banner_url)

    @classmethod
    def from_text(cls, client: Client, text: str) -> Self:
        soup = cls.__to_soup(text)
        title = cls.__get_title(soup)
        banner_url = cls.__get_banner_url(soup)
        return cls(client, title, banner_url)
