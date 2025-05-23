import logging
import random
import re
from copy import copy
from pathlib import Path
from typing import Optional, Union, Type, Dict, Set, List, Tuple, TypedDict
from string import Formatter
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from ..connection import Connection
from ..objects import (
    Song,
    Source,
    Album,
    Artist,
    Target,
    DatabaseObject,
    Options,
    Collection,
    Label,
)
from ..utils.enums import SourceType
from ..utils.enums.album import AlbumType
from ..audio import write_metadata_to_target, correct_codec
from ..utils.config import main_settings
from ..utils.support_classes.query import Query
from ..utils.support_classes.download_result import DownloadResult
from ..utils.string_processing import fit_to_file_system
from ..utils import trace, output, BColors

INDEPENDENT_DB_OBJECTS = Union[Label, Album, Artist, Song]
INDEPENDENT_DB_TYPES = Union[Type[Song], Type[Album], Type[Artist], Type[Label]]

@dataclass
class FetchOptions:
    download_all: bool = False
    album_type_blacklist: Set[AlbumType] = field(default_factory=lambda: set(AlbumType(a) for a in main_settings["album_type_blacklist"]))

@dataclass
class DownloadOptions:
    download_all: bool = False
    album_type_blacklist: Set[AlbumType] = field(default_factory=lambda: set(AlbumType(a) for a in main_settings["album_type_blacklist"]))

    process_audio_if_found: bool = False
    process_metadata_if_found: bool = True

class Page:
    SOURCE_TYPE: SourceType
    LOGGER: logging.Logger

    def __new__(cls, *args, **kwargs):
        cls.LOGGER = logging.getLogger(cls.__name__)

        return super().__new__(cls)

    def __init__(self, download_options: DownloadOptions = None, fetch_options: FetchOptions = None):
        self.SOURCE_TYPE.register_page(self)
        
        self.download_options: DownloadOptions = download_options or DownloadOptions()
        self.fetch_options: FetchOptions = fetch_options or FetchOptions()

    def _search_regex(self, pattern, string, default=None, fatal=True, flags=0, group=None):
        """
        Perform a regex search on the given string, using a single or a list of
        patterns returning the first matching group.
        In case of failure return a default value or raise a WARNING or a
        RegexNotFoundError, depending on fatal, specifying the field name.
        """

        if isinstance(pattern, str):
            mobj = re.search(pattern, string, flags)
        else:
            for p in pattern:
                mobj = re.search(p, string, flags)
                if mobj:
                    break

        if mobj:
            if group is None:
                # return the first matching group
                return next(g for g in mobj.groups() if g is not None)
            elif isinstance(group, (list, tuple)):
                return tuple(mobj.group(g) for g in group)
            else:
                return mobj.group(group)

        return default

    def get_source_type(self, source: Source) -> Optional[Type[DatabaseObject]]:
        return None

    def get_soup_from_response(self, r: requests.Response) -> BeautifulSoup:
        return BeautifulSoup(r.content, "html.parser")

    # to search stuff
    def search(self, query: Query) -> List[DatabaseObject]:
        music_object = query.music_object

        search_functions = {
            Song: self.song_search,
            Album: self.album_search,
            Artist: self.artist_search,
            Label: self.label_search
        }

        if type(music_object) in search_functions:
            r = search_functions[type(music_object)](music_object)
            if r is not None and len(r) > 0:
                return r

        r = []
        for default_query in query.default_search:
            for single_option in self.general_search(default_query):
                r.append(single_option)

        return r

    def general_search(self, search_query: str) -> List[DatabaseObject]:
        return []

    def label_search(self, label: Label) -> List[Label]:
        return []

    def artist_search(self, artist: Artist) -> List[Artist]:
        return []

    def album_search(self, album: Album) -> List[Album]:
        return []

    def song_search(self, song: Song) -> List[Song]:
        return []

    # to fetch stuff
    def fetch_song(self, source: Source, stop_at_level: int = 1) -> Song:
        return Song()

    def fetch_album(self, source: Source, stop_at_level: int = 1) -> Album:
        return Album()

    def fetch_artist(self, source: Source, stop_at_level: int = 1) -> Artist:
        return Artist()

    def fetch_label(self, source: Source, stop_at_level: int = 1) -> Label:
        return Label()

    # to download stuff
    def get_skip_intervals(self, song: Song, source: Source) -> List[Tuple[float, float]]:
        return []

    def post_process_hook(self, song: Song, temp_target: Target, **kwargs):
        pass

    def download_song_to_target(self, source: Source, target: Target, desc: str = None) -> DownloadResult:
        return DownloadResult()
