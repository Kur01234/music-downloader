from __future__ import annotations

from collections import defaultdict
from enum import Enum
from typing import (
    List, 
    Dict, 
    Set, 
    Tuple, 
    Optional, 
    Iterable, 
    Generator, 
    TypedDict, 
    Callable, 
    Any,
    TYPE_CHECKING
)
from urllib.parse import urlparse, ParseResult
from dataclasses import dataclass, field
from functools import cached_property

from ..utils import generate_id
from ..utils.enums import SourceType, ALL_SOURCE_TYPES
from ..utils.config import youtube_settings
from ..utils.string_processing import hash_url, shorten_display_url

from .metadata import Mapping, Metadata
if TYPE_CHECKING:
    from ..pages.abstract import Page



@dataclass
class Source:
    source_type: SourceType
    url: str
    referrer_page: SourceType = None
    audio_url: Optional[str] = None

    additional_data: dict = field(default_factory=dict)

    def __post_init__(self):
        self.referrer_page = self.referrer_page or self.source_type

    @classmethod
    def match_url(cls, url: str, referrer_page: SourceType) -> Optional[Source]:
        """
        this shouldn't be used, unless you are not certain what the source is for
        the reason is that it is more inefficient
        """
        parsed_url = urlparse(url)
        url = parsed_url.geturl()
        
        if "musify" in parsed_url.netloc:
            return cls(ALL_SOURCE_TYPES.MUSIFY, url, referrer_page=referrer_page)

        if parsed_url.netloc in [_url.netloc for _url in youtube_settings['youtube_url']]:
            return cls(ALL_SOURCE_TYPES.YOUTUBE, url, referrer_page=referrer_page)

        if url.startswith("https://www.deezer"):
            return cls(ALL_SOURCE_TYPES.DEEZER, url, referrer_page=referrer_page)
        
        if url.startswith("https://open.spotify.com"):
            return cls(ALL_SOURCE_TYPES.SPOTIFY, url, referrer_page=referrer_page)

        if "bandcamp" in url:
            return cls(ALL_SOURCE_TYPES.BANDCAMP, url, referrer_page=referrer_page)

        if "wikipedia" in parsed_url.netloc:
            return cls(ALL_SOURCE_TYPES.WIKIPEDIA, url, referrer_page=referrer_page)

        if url.startswith("https://www.metal-archives.com/"):
            return cls(ALL_SOURCE_TYPES.ENCYCLOPAEDIA_METALLUM, url, referrer_page=referrer_page)

        # the less important once
        if url.startswith("https://www.facebook"):
            return cls(ALL_SOURCE_TYPES.FACEBOOK, url, referrer_page=referrer_page)

        if url.startswith("https://www.instagram"):
            return cls(ALL_SOURCE_TYPES.INSTAGRAM, url, referrer_page=referrer_page)

        if url.startswith("https://twitter"):
            return cls(ALL_SOURCE_TYPES.TWITTER, url, referrer_page=referrer_page)

        if url.startswith("https://myspace.com"):
            return cls(ALL_SOURCE_TYPES.MYSPACE, url, referrer_page=referrer_page)

    @property
    def has_page(self) -> bool:
        return self.source_type.page is not None
    
    @property
    def page(self) -> Page:
        return self.source_type.page

    @property
    def parsed_url(self) -> ParseResult:
        return urlparse(self.url)

    @property
    def hash_url(self) -> str:
        return hash_url(self.url)

    @property
    def indexing_values(self) -> list:
        r = [hash_url(self.url)]
        if self.audio_url:
            r.append(hash_url(self.audio_url))
        return r

    def __repr__(self) -> str:
        return f"Src({self.source_type.value}: {shorten_display_url(self.url)})"

    def __merge__(self, other: Source, **kwargs):
        if self.audio_url is None:
            self.audio_url = other.audio_url
        self.additional_data.update(other.additional_data)

    page_str = property(fget=lambda self: self.source_type.value)


class SourceTypeSorting(TypedDict):
    sort_key: Callable[[SourceType], Any]
    reverse: bool
    only_with_page: bool


class SourceCollection:
    __change_version__ = generate_id()

    _indexed_sources: Dict[str, Source]
    _sources_by_type: Dict[SourceType, List[Source]]

    def __init__(self, data: Optional[Iterable[Source]] = None, **kwargs):
        self._sources_by_type = defaultdict(list)
        self._indexed_sources = {}

        self.extend(data or [])

    def source_types(
        self, 
        only_with_page: bool = False, 
        sort_key = lambda page: page.name, 
        reverse: bool = False
    ) -> Iterable[SourceType]:
        """
        Returns a list of all source types contained in this source collection.

        Args:
            only_with_page (bool, optional): If True, only returns source types that have a page, meaning you can download from them.
            sort_key (function, optional): A function that defines the sorting key for the source types. Defaults to lambda page: page.name.
            reverse (bool, optional): If True, sorts the source types in reverse order. Defaults to False.

        Returns:
            Iterable[SourceType]: A list of source types.
        """

        source_types: List[SourceType] = self._sources_by_type.keys()
        if only_with_page:
            source_types = filter(lambda st: st.has_page, source_types)

        return sorted(
            source_types, 
            key=sort_key, 
            reverse=reverse
        )

    def get_sources(self, *source_types: List[SourceType], source_type_sorting: SourceTypeSorting = None) -> Generator[Source]:
            """
            Retrieves sources based on the provided source types and source type sorting.

            Args:
                *source_types (List[Source]): Variable number of source types to filter the sources.
                source_type_sorting (SourceTypeSorting): Sorting criteria for the source types. This is only relevant if no source types are provided.

            Yields:
                Generator[Source]: A generator that yields the sources based on the provided filters.

            Returns:
                None
            """
            if not len(source_types):
                source_type_sorting = source_type_sorting or {}
                source_types = self.source_types(**source_type_sorting)

            for source_type in source_types:
                yield from self._sources_by_type[source_type]

    def append(self, source: Source):
        if source is None:
            return

        existing_source = None
        for key in source.indexing_values:
            if key in self._indexed_sources:
                existing_source = self._indexed_sources[key]
                break

        if existing_source is not None:
            existing_source.__merge__(source)
            source = existing_source
        else:
            self._sources_by_type[source.source_type].append(source)

        changed = False
        for key in source.indexing_values:
            if key not in self._indexed_sources:
                changed = True
            self._indexed_sources[key] = source

        if changed:
            self.__change_version__ = generate_id()

    def extend(self, sources: Iterable[Source]):
        for source in sources:
            self.append(source)

    def __iter__(self):
        yield from self.get_sources()

    def __merge__(self, other: SourceCollection, **kwargs):
        self.extend(other)
        
    @property
    def hash_url_list(self) -> List[str]:
        return [hash_url(source.url) for source in self.get_sources()]

    @property
    def url_list(self) -> List[str]:
        return [source.url for source in self.get_sources()]

    @property
    def homepage_list(self) -> List[str]:
        return [source_type.homepage for source_type in self._sources_by_type.keys()]

    def indexing_values(self) -> Generator[Tuple[str, str], None, None]:
        for index in self._indexed_sources:
            yield "url", index