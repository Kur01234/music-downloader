from typing import Tuple, Type, Dict, Set, Optional, List
from collections import defaultdict
from pathlib import Path
import re
import logging

from . import FetchOptions, DownloadOptions
from .results import SearchResults
from ..objects import (
    DatabaseObject as DataObject,
    Collection,
    Target,
    Source,
    Options,
    Song,
    Album,
    Artist,
    Label,
)
from ..audio import write_metadata_to_target, correct_codec
from ..utils import output, BColors
from ..utils.string_processing import fit_to_file_system
from ..utils.config import youtube_settings, main_settings
from ..utils.path_manager import LOCATIONS
from ..utils.enums import SourceType, ALL_SOURCE_TYPES
from ..utils.support_classes.download_result import DownloadResult
from ..utils.support_classes.query import Query
from ..utils.support_classes.download_result import DownloadResult
from ..utils.exception import MKMissingNameException
from ..utils.exception.download import UrlNotFoundException
from ..utils.shared import DEBUG_PAGES

from ..pages import Page, EncyclopaediaMetallum, Musify, YouTube, YoutubeMusic, Bandcamp, Musicbrainz, Genius, INDEPENDENT_DB_OBJECTS


ALL_PAGES: Set[Type[Page]] = {
    # EncyclopaediaMetallum,
    Genius,
    Musify,
    YoutubeMusic,
    Bandcamp,
    Musicbrainz
}

if youtube_settings["use_youtube_alongside_youtube_music"]:
    ALL_PAGES.add(YouTube)

AUDIO_PAGES: Set[Type[Page]] = {
    Musify,
    YouTube,
    YoutubeMusic,
    Bandcamp
}

SHADY_PAGES: Set[Type[Page]] = {
    Musify,
}

fetch_map = {
    Song: "fetch_song",
    Album: "fetch_album",
    Artist: "fetch_artist",
    Label: "fetch_label",
}

if DEBUG_PAGES:
    DEBUGGING_PAGE = Bandcamp
    print(f"Only downloading from page {DEBUGGING_PAGE}.")

    ALL_PAGES = {DEBUGGING_PAGE}
    AUDIO_PAGES = ALL_PAGES.union(AUDIO_PAGES)


class Pages:
    def __init__(self, exclude_pages: Set[Type[Page]] = None, exclude_shady: bool = False, download_options: DownloadOptions = None, fetch_options: FetchOptions = None):
        self.LOGGER = logging.getLogger("download")
        
        self.download_options: DownloadOptions = download_options or DownloadOptions()
        self.fetch_options: FetchOptions = fetch_options or FetchOptions()

        # initialize all page instances
        self._page_instances: Dict[Type[Page], Page] = dict()
        self._source_to_page: Dict[SourceType, Type[Page]] = dict()
        
        exclude_pages = exclude_pages if exclude_pages is not None else set()
        
        if exclude_shady:
            exclude_pages = exclude_pages.union(SHADY_PAGES)
        
        if not exclude_pages.issubset(ALL_PAGES):
            raise ValueError(f"The excluded pages have to be a subset of all pages: {exclude_pages} | {ALL_PAGES}")
        
        def _set_to_tuple(page_set: Set[Type[Page]]) -> Tuple[Type[Page], ...]:
            return tuple(sorted(page_set, key=lambda page: page.__name__))
        
        self._pages_set: Set[Type[Page]] = ALL_PAGES.difference(exclude_pages)
        self.pages: Tuple[Type[Page], ...] = _set_to_tuple(self._pages_set)

        self._audio_pages_set: Set[Type[Page]] = self._pages_set.intersection(AUDIO_PAGES)
        self.audio_pages: Tuple[Type[Page], ...] = _set_to_tuple(self._audio_pages_set)
        
        for page_type in self.pages:
            self._page_instances[page_type] = page_type(fetch_options=self.fetch_options, download_options=self.download_options)
            self._source_to_page[page_type.SOURCE_TYPE] = page_type

    def _get_page_from_enum(self, source_page: SourceType) -> Page:
        if source_page not in self._source_to_page:
            return None
        return self._page_instances[self._source_to_page[source_page]]

    def search(self, query: Query) -> SearchResults:
        result = SearchResults()
        
        for page_type in self.pages:
            result.add(
                page=page_type,
                search_result=self._page_instances[page_type].search(query=query)
            )
            
        return result
    
    def fetch_details(self, data_object: DataObject, stop_at_level: int = 1, **kwargs) -> DataObject:
        if not isinstance(data_object, INDEPENDENT_DB_OBJECTS):
            return data_object
        
        source: Source
        for source in data_object.source_collection.get_sources(source_type_sorting={
            "only_with_page": True,
        }):
            new_data_object = self.fetch_from_source(source=source, stop_at_level=stop_at_level)
            if new_data_object is not None:
                data_object.merge(new_data_object)

        return data_object

    def fetch_from_source(self, source: Source, **kwargs) -> Optional[DataObject]:
        if not source.has_page:
            return None
        
        source_type = source.page.get_source_type(source=source)
        if source_type is None:
            self.LOGGER.debug(f"Could not determine source type for {source}.")
            return None

        func = getattr(source.page, fetch_map[source_type])
        
        # fetching the data object and marking it as fetched
        data_object: DataObject = func(source=source, **kwargs)
        data_object.mark_as_fetched(source.hash_url)
        return data_object

    def fetch_from_url(self, url: str) -> Optional[DataObject]:
        source = Source.match_url(url, ALL_SOURCE_TYPES.MANUAL)
        if source is None:
            return None
        
        return self.fetch_from_source(source=source)
    
    def _skip_object(self, data_object: DataObject) -> bool:
        if isinstance(data_object, Album):
            if not self.download_options.download_all and data_object.album_type in self.download_options.album_type_blacklist:
                return True
        
        return False

    def download(self, data_object: DataObject, genre: str, **kwargs) -> DownloadResult:
        # fetch the given object
        self.fetch_details(data_object)
        output(f"\nDownloading {data_object.option_string}...", color=BColors.BOLD)
        
        # fetching all parent objects (e.g. if you only download a song)
        if not kwargs.get("fetched_upwards", False):
            to_fetch: List[DataObject] = [data_object]

            while len(to_fetch) > 0:
                new_to_fetch = []
                for d in to_fetch:
                    if self._skip_object(d):
                        continue

                    self.fetch_details(d)

                    for c in d.get_parent_collections():
                        new_to_fetch.extend(c)

                to_fetch = new_to_fetch
            
            kwargs["fetched_upwards"] = True
        
        # download all children
        download_result: DownloadResult = DownloadResult()
        for c in data_object.get_child_collections():
            for d in c:
                if self._skip_object(d):
                    continue

                download_result.merge(self.download(d, genre, **kwargs))

        # actually download if the object is a song
        if isinstance(data_object, Song):
            """
            TODO
            add the traced artist and album to the naming.
            I am able to do that, because duplicate values are removed later on.
            """

            self._download_song(data_object, naming={
                "genre": [genre],
                "audio_format": [main_settings["audio_format"]],
            })

        return download_result

    def _extract_fields_from_template(self, path_template: str) -> Set[str]:
        return set(re.findall(r"{([^}]+)}", path_template))

    def _parse_path_template(self, path_template: str, naming: Dict[str, List[str]]) -> str:
        field_names: Set[str] = self._extract_fields_from_template(path_template)
        
        for field in field_names:
            if len(naming[field]) == 0:
                raise MKMissingNameException(f"Missing field for {field}.")

            path_template = path_template.replace(f"{{{field}}}", naming[field][0])

        return path_template

    def _download_song(self, song: Song, naming: dict) -> DownloadOptions:
        """
        TODO
        Search the song in the file system.
        """
        r = DownloadResult(total=1)
        
        # pre process the data recursively
        song.compile()
        
        # manage the naming
        naming: Dict[str, List[str]] = defaultdict(list, naming)
        naming["song"].append(song.title_value)
        naming["isrc"].append(song.isrc)
        naming["album"].extend(a.title_value for a in song.album_collection)
        naming["album_type"].extend(a.album_type.value for a in song.album_collection)
        naming["artist"].extend(a.name for a in song.artist_collection)
        naming["artist"].extend(a.name for a in song.feature_artist_collection)
        for a in song.album_collection:
            naming["label"].extend([l.title_value for l in a.label_collection])
        # removing duplicates from the naming, and process the strings
        for key, value in naming.items():
            # https://stackoverflow.com/a/17016257
            naming[key] = list(dict.fromkeys(value))
        song.genre = naming["genre"][0]

        # manage the targets
        tmp: Target = Target.temp(file_extension=main_settings["audio_format"])

        song.target_collection.append(Target(
            relative_to_music_dir=True,
            file_path=Path(
                self._parse_path_template(main_settings["download_path"], naming=naming), 
                self._parse_path_template(main_settings["download_file"], naming=naming),
            )
        ))
        for target in song.target_collection:
            if target.exists:
                output(f'{target.file_path} {BColors.OKGREEN.value}[already exists]', color=BColors.GREY)
                r.found_on_disk += 1

                if not self.download_options.download_again_if_found:
                    target.copy_content(tmp)
            else:
                target.create_path()
                output(f'{target.file_path}', color=BColors.GREY)

        # this streams from every available source until something succeeds, setting the skip intervals to the values of the according source
        used_source: Optional[Source] = None
        skip_intervals: List[Tuple[float, float]] = []
        for source in song.source_collection.get_sources(source_type_sorting={
            "only_with_page": True,
            "sort_key": lambda page: page.download_priority,
            "reverse": True,
        }):
            if tmp.exists:
                break

            used_source = source
            streaming_results = source.page.download_song_to_target(source=source, target=tmp, desc="download")
            skip_intervals = source.page.get_skip_intervals(song=song, source=source)

            # if something has been downloaded but it somehow failed, delete the file
            if streaming_results.is_fatal_error and tmp.exists:
                tmp.delete()

        # if everything went right, the file should exist now
        if not tmp.exists:
            if used_source is None:
                r.error_message = f"No source found for {song.option_string}."
            else:
                r.error_message = f"Something went wrong downloading {song.option_string}."
            return r

        # post process the audio
        found_on_disk = used_source is None
        if not found_on_disk or self.download_options.process_audio_if_found:
            correct_codec(target=tmp, skip_intervals=skip_intervals)
            r.sponsor_segments = len(skip_intervals)

        if used_source is not None:
            used_source.page.post_process_hook(song=song, temp_target=tmp)

        if not found_on_disk or self.download_options.process_metadata_if_found:
            write_metadata_to_target(metadata=song.metadata, target=tmp, song=song)

        # copy the tmp target to the final locations
        for target in song.target_collection:
            tmp.copy_content(target)

        tmp.delete()
        return r

    def fetch_url(self, url: str, stop_at_level: int = 2) -> Tuple[Type[Page], DataObject]:
        source = Source.match_url(url, ALL_SOURCE_TYPES.MANUAL)
        
        if source is None:
            raise UrlNotFoundException(url=url)
        
        _actual_page = self._source_to_page[source.source_type]
        
        return _actual_page, self._page_instances[_actual_page].fetch_object_from_source(source=source, stop_at_level=stop_at_level)