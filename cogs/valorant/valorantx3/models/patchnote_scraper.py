from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from valorantx2.valorant_api import Asset

if TYPE_CHECKING:
    from ..client import Client
    from typing_extensions import Self

from bs4 import BeautifulSoup, FeatureNotFound

# fmt: off
__all__ = (
    'PatchNoteScraper',
)
# fmt: on


class PatchNoteScraper:
    def __init__(self, client: Client, title: Optional[str], banner_url: Optional[str]) -> None:
        self._client: Client = client
        self._title: Optional[str] = title
        self._banner_url: Optional[str] = banner_url

    def __repr__(self) -> str:
        return f'<PatchNote title={self.title!r}> banner={self.banner!r}>'

    @property
    def title(self) -> Optional[str]:
        return self._title

    @property
    def banner(self) -> Optional[Asset]:
        if self._banner_url is None:
            return None
        return Asset._from_url(self._client.valorant_api._cache, self._banner_url)

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
    def __get_title(soup: BeautifulSoup) -> Optional[str]:
        soup_title = soup.find('title')
        if soup_title is not None:
            return soup_title.text
        return None

    @staticmethod
    def __get_banner_url(soup: BeautifulSoup) -> Optional[str]:
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
