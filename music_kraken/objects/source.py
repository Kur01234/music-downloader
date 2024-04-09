from collections import defaultdict
from enum import Enum
from typing import List, Dict, Set, Tuple, Optional, Iterable
from urllib.parse import urlparse

from ..utils.enums.source import SourcePages, SourceTypes
from ..utils.config import youtube_settings

from .metadata import Mapping, Metadata
from .parents import OuterProxy
from .collection import Collection


class Source(OuterProxy):
    url: str

    page_enum: SourcePages
    referer_page: SourcePages

    audio_url: str

    _default_factories = {
        "audio_url": lambda: None,
    }

    # This is automatically generated
    def __init__(self, page_enum: SourcePages, url: str, referer_page: SourcePages = None, audio_url: str = None,
                 **kwargs) -> None:

        if referer_page is None:
            referer_page = page_enum

        super().__init__(url=url, page_enum=page_enum, referer_page=referer_page, audio_url=audio_url, **kwargs)

    @classmethod
    def match_url(cls, url: str, referer_page: SourcePages) -> Optional["Source"]:
        """
        this shouldn't be used, unlesse you are not certain what the source is for
        the reason is that it is more inefficient
        """
        parsed = urlparse(url)
        url = parsed.geturl()
        
        if "musify" in parsed.netloc:
            return cls(SourcePages.MUSIFY, url, referer_page=referer_page)

        if parsed.netloc in [_url.netloc for _url in youtube_settings['youtube_url']]:
            return cls(SourcePages.YOUTUBE, url, referer_page=referer_page)

        if url.startswith("https://www.deezer"):
            return cls(SourcePages.DEEZER, url, referer_page=referer_page)
        
        if url.startswith("https://open.spotify.com"):
            return cls(SourcePages.SPOTIFY, url, referer_page=referer_page)

        if "bandcamp" in url:
            return cls(SourcePages.BANDCAMP, url, referer_page=referer_page)

        if "wikipedia" in parsed.netloc:
            return cls(SourcePages.WIKIPEDIA, url, referer_page=referer_page)

        if url.startswith("https://www.metal-archives.com/"):
            return cls(SourcePages.ENCYCLOPAEDIA_METALLUM, url, referer_page=referer_page)

        # the less important once
        if url.startswith("https://www.facebook"):
            return cls(SourcePages.FACEBOOK, url, referer_page=referer_page)

        if url.startswith("https://www.instagram"):
            return cls(SourcePages.INSTAGRAM, url, referer_page=referer_page)

        if url.startswith("https://twitter"):
            return cls(SourcePages.TWITTER, url, referer_page=referer_page)

        if url.startswith("https://myspace.com"):
            return cls(SourcePages.MYSPACE, url, referer_page=referer_page)

    def get_song_metadata(self) -> Metadata:
        return Metadata({
            Mapping.FILE_WEBPAGE_URL: [self.url],
            Mapping.SOURCE_WEBPAGE_URL: [self.homepage]
        })

    def get_artist_metadata(self) -> Metadata:
        return Metadata({
            Mapping.ARTIST_WEBPAGE_URL: [self.url]
        })

    @property
    def metadata(self) -> Metadata:
        return self.get_song_metadata()

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('id', self.id),
            ('url', self.url),
            ('audio_url', self.audio_url),
        ]

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return f"Src({self.page_enum.value}: {self.url}, {self.audio_url})"

    page_str = property(fget=lambda self: self.page_enum.value)
    type_str = property(fget=lambda self: self.type_enum.value)
    homepage = property(fget=lambda self: SourcePages.get_homepage(self.page_enum))


class SourceCollection(Collection):
    def __init__(self, data: Optional[Iterable[Source]] = None, **kwargs):
        self._page_to_source_list: Dict[SourcePages, List[Source]] = defaultdict(list)

        super().__init__(data=data, **kwargs)

    def _map_element(self, __object: Source, **kwargs):
        super()._map_element(__object, **kwargs)

        self._page_to_source_list[__object.page_enum].append(__object)
        
    @property
    def source_pages(self) -> Set[SourcePages]:
        return set(source.page_enum for source in self._data)

    def get_sources_from_page(self, source_page: SourcePages) -> List[Source]:
        """
        getting the sources for a specific page like
        YouTube or musify
        """
        return self._page_to_source_list[source_page].copy()
