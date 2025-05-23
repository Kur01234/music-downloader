from __future__ import annotations

import random
from collections import defaultdict
from typing import List, Optional, Dict, Tuple, Type, Union
import copy

import pycountry

from ..utils.enums.album import AlbumType, AlbumStatus
from .collection import Collection
from .formatted_text import FormattedText
from .lyrics import Lyrics
from .contact import Contact
from .artwork import Artwork
from .metadata import (
    Mapping as id3Mapping,
    ID3Timestamp,
    Metadata
)
from .option import Options
from .parents import OuterProxy, P
from .source import Source, SourceCollection
from .target import Target
from .country import Language, Country
from ..utils.shared import DEBUG_PRINT_ID
from ..utils.string_processing import unify

from .parents import OuterProxy as Base

from ..utils.config import main_settings
from ..utils.enums.colors import BColors

"""
All Objects dependent 
"""

CountryTyping = type(list(pycountry.countries)[0])

OPTION_BACKGROUND = BColors.GREY
OPTION_FOREGROUND = BColors.OKBLUE

def get_collection_string(
    collection: Collection[Base], 
    template: str, 
    ignore_titles: Set[str] = None,
    background: BColors = OPTION_BACKGROUND, 
    foreground: BColors = OPTION_FOREGROUND,
    add_id: bool = DEBUG_PRINT_ID,
) -> str:
    if collection.empty:
        return ""

    foreground = foreground.value
    background = background.value

    ignore_titles = ignore_titles or set()

    r = background

    def get_element_str(element) -> str:
        nonlocal add_id
        r = element.title_string.strip()
        if add_id and False:
            r += " " + str(element.id)
        return r

    element: Base
    titel_list: List[str] = [get_element_str(element) for element in collection if element.title_string not in ignore_titles]

    for i, titel in enumerate(titel_list):
        delimiter = ", "
        if i == len(collection) - 1:
            delimiter = ""
        elif i == len(collection) - 2:
            delimiter = " and "

        r += foreground + titel + BColors.ENDC.value + background + delimiter + BColors.ENDC.value

    r += BColors.ENDC.value

    return template.format(r)

class Song(Base):
    title: str
    unified_title: str
    isrc: str
    length: int
    genre: str
    note: FormattedText
    tracksort: int
    artwork: Artwork

    source_collection: SourceCollection
    target_collection: Collection[Target]
    lyrics_collection: Collection[Lyrics]

    artist_collection: Collection[Artist]
    feature_artist_collection: Collection[Artist]
    album_collection: Collection[Album]

    _default_factories = {
        "note": FormattedText,
        "length": lambda: 0,
        "source_collection": SourceCollection,
        "target_collection": Collection,
        "lyrics_collection": Collection,
        "artwork": Artwork,

        "album_collection": Collection,
        "artist_collection": Collection,
        "feature_artist_collection": Collection,

        "title": lambda: None,
        "unified_title": lambda: None,
        "isrc": lambda: None,
        "genre": lambda: None,

        "tracksort": lambda: 0,
    }

    def __init__(
        self, 
        title: str = None, 
        isrc: str = None, 
        length: int = None,
        genre: str = None, 
        note: FormattedText = None, 
        source_list: List[Source] = None,
        target_list: List[Target] = None, 
        lyrics_list: List[Lyrics] = None,
        artist_list: List[Artist] = None, 
        feature_artist_list: List[Artist] = None,
        album_list: List[Album] = None, 
        tracksort: int = 0, 
        artwork: Optional[Artwork] = None, 
        **kwargs
    ) -> None:
        real_kwargs = copy.copy(locals())
        real_kwargs.update(real_kwargs.pop("kwargs", {}))

        Base.__init__(**real_kwargs)

    UPWARDS_COLLECTION_STRING_ATTRIBUTES = ("artist_collection", "feature_artist_collection", "album_collection")
    TITEL = "title"

    def __init_collections__(self) -> None:
        self.feature_artist_collection.push_to = [self.artist_collection]
        self.artist_collection.pull_from = [self.feature_artist_collection]

        self.album_collection.sync_on_append = {
            "artist_collection": self.artist_collection,
        }

        self.album_collection.append_object_to_attribute = {
            "song_collection": self,
        }
        self.artist_collection.extend_object_to_attribute = {
            "album_collection": self.album_collection
        }
        self.feature_artist_collection.extend_object_to_attribute = {
            "album_collection": self.album_collection
        }

    def _add_other_db_objects(self, object_type: Type[OuterProxy], object_list: List[OuterProxy]):
        if object_type is Song:
            return

        if isinstance(object_list, Lyrics):
            self.lyrics_collection.extend(object_list)
            return

        if isinstance(object_list, Artist):
            self.feature_artist_collection.extend(object_list)
            return

        if isinstance(object_list, Album):
            self.album_collection.extend(object_list)
            return

    INDEX_DEPENDS_ON = ("title", "isrc", "source_collection")

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('title', unify(self.title)),
            ('isrc', self.isrc),
            *self.source_collection.indexing_values(),
        ]

    @property
    def metadata(self) -> Metadata:
        metadata = Metadata({
            id3Mapping.TITLE: [self.title],
            id3Mapping.ISRC: [self.isrc],
            id3Mapping.LENGTH: [self.length],
            id3Mapping.GENRE: [self.genre],
            id3Mapping.TRACKNUMBER: [self.tracksort_str],
            id3Mapping.COMMENT: [self.note.markdown],
            id3Mapping.FILE_WEBPAGE_URL: self.source_collection.url_list,
            id3Mapping.SOURCE_WEBPAGE_URL: self.source_collection.homepage_list,
        })

        # metadata.merge_many([s.get_song_metadata() for s in self.source_collection])  album sources have no relevant metadata for id3
        metadata.merge_many([a.metadata for a in self.album_collection])
        metadata.merge_many([a.metadata for a in self.artist_collection])
        metadata.merge_many([a.metadata for a in self.feature_artist_collection])
        metadata.merge_many([lyrics.metadata for lyrics in self.lyrics_collection])

        return metadata

    def get_artist_credits(self) -> str:
        main_artists = ", ".join([artist.name for artist in self.artist_collection])
        feature_artists = ", ".join([artist.name for artist in self.feature_artist_collection])

        if len(feature_artists) == 0:
            return main_artists
        return f"{main_artists} feat. {feature_artists}"

    @property
    def option_string(self) -> str:
        r = "song "
        r += OPTION_FOREGROUND.value + self.title_string + BColors.ENDC.value + OPTION_BACKGROUND.value
        r += get_collection_string(self.album_collection, " from {}", ignore_titles={self.title})
        r += get_collection_string(self.artist_collection, " by {}")
        r += get_collection_string(self.feature_artist_collection, " feat. {}" if len(self.artist_collection) > 0 else " by {}")
        return r

    @property
    def tracksort_str(self) -> str:
        """
        if the album tracklist is empty, it sets it length to 1, this song has to be on the Album
        :returns id3_tracksort: {song_position}/{album.length_of_tracklist} 
        """
        if len(self.album_collection) == 0:
            return f"{self.tracksort}"

        return f"{self.tracksort}/{len(self.album_collection[0].song_collection) or 1}"


class Album(Base):
    title: str
    unified_title: str
    album_status: AlbumStatus
    album_type: AlbumType
    language: Language
    date: ID3Timestamp
    barcode: str
    albumsort: int
    notes: FormattedText

    source_collection: SourceCollection

    song_collection: Collection[Song]
    artist_collection: Collection[Artist]
    feature_artist_collection: Collection[Artist]
    label_collection: Collection[Label]

    _default_factories = {
        "title": lambda: None,
        "unified_title": lambda: None,
        "album_status": lambda: None,
        "barcode": lambda: None,
        "albumsort": lambda: None,

        "album_type": lambda: AlbumType.OTHER,
        "language": lambda: Language.by_alpha_2("en"),
        "date": ID3Timestamp,
        "notes": FormattedText,

        "source_collection": SourceCollection,

        "song_collection": Collection,
        "artist_collection": Collection,
        "feature_artist_collection": Collection,
        "label_collection": Collection,
    }

    TITEL = "title"

    # This is automatically generated
    def __init__(
        self, 
        title: str = None, 
        unified_title: str = None, 
        album_status: AlbumStatus = None,
        album_type: AlbumType = None, 
        language: Language = None, 
        date: ID3Timestamp = None,
        barcode: str = None, 
        albumsort: int = None, 
        notes: FormattedText = None,
        source_list: List[Source] = None, 
        artist_list: List[Artist] = None, 
        song_list: List[Song] = None,
        label_list: List[Label] = None, 
        **kwargs
    ) -> None:
        real_kwargs = copy.copy(locals())
        real_kwargs.update(real_kwargs.pop("kwargs", {}))

        Base.__init__(**real_kwargs)

    DOWNWARDS_COLLECTION_STRING_ATTRIBUTES = ("song_collection",)
    UPWARDS_COLLECTION_STRING_ATTRIBUTES = ("label_collection", "artist_collection")

    def __init_collections__(self):
        self.feature_artist_collection.push_to = [self.artist_collection]
        self.artist_collection.pull_from = [self.feature_artist_collection]

        self.song_collection.append_object_to_attribute = {
            "album_collection": self
        }
        self.song_collection.sync_on_append = {
            "artist_collection": self.artist_collection
        }

        self.artist_collection.append_object_to_attribute = {
            "album_collection": self
        }
        self.artist_collection.extend_object_to_attribute = {
            "label_collection": self.label_collection
        }

    def _add_other_db_objects(self, object_type: Type[OuterProxy], object_list: List[OuterProxy]):
        if object_type is Song:
            self.song_collection.extend(object_list)
            return

        if object_type is Artist:
            self.artist_collection.extend(object_list)
            return

        if object_type is Album:
            return

        if object_type is Label:
            self.label_collection.extend(object_list)
            return

    INDEX_DEPENDS_ON = ("title", "barcode", "source_collection")

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('title', unify(self.title)),
            ('barcode', self.barcode),
            *self.source_collection.indexing_values(),
        ]

    @property
    def metadata(self) -> Metadata:
        """
        TODO
        - barcode
        :return:
        """
        return Metadata({
            id3Mapping.ALBUM: [self.title],
            id3Mapping.COPYRIGHT: [self.copyright],
            id3Mapping.LANGUAGE: [self.iso_639_2_lang],
            id3Mapping.ALBUM_ARTIST: [a.name for a in self.artist_collection],
            id3Mapping.DATE: [self.date.strftime("%d%m")] if self.date.has_year and self.date.has_month else [],
            id3Mapping.TIME: [self.date.strftime(("%H%M"))] if self.date.has_hour and self.date.has_minute else [],
            id3Mapping.YEAR: [str(self.date.year).zfill(4)] if self.date.has_year else [],
            id3Mapping.RELEASE_DATE: [self.date.timestamp],
            id3Mapping.ORIGINAL_RELEASE_DATE: [self.date.timestamp],
            id3Mapping.ALBUMSORTORDER: [str(self.albumsort)] if self.albumsort is not None else []
        })

    @property
    def option_string(self) -> str:
        r = "album "
        r += OPTION_FOREGROUND.value + self.title_string + BColors.ENDC.value + OPTION_BACKGROUND.value
        r += get_collection_string(self.artist_collection, " by {}")
        if len(self.artist_collection) <= 0:
            r += get_collection_string(self.feature_artist_collection, " by {}")
        r += get_collection_string(self.label_collection, " under {}")

        if len(self.song_collection) > 0:
            r += f" with {len(self.song_collection)} songs"
        return r

    def _compile(self):
        self.analyze_implied_album_type()
        self.update_tracksort()
        self.fix_artist_collection()

    def analyze_implied_album_type(self):
        # if the song collection has only one song, it is reasonable to assume that it is a single
        if len(self.song_collection) == 1:
            self.album_type = AlbumType.SINGLE
            return

        # if the album already has an album type, we don't need to do anything
        if self.album_type is not AlbumType.OTHER:
            return

        # for information on EP's I looked at https://www.reddit.com/r/WeAreTheMusicMakers/comments/a354ql/whats_the_cutoff_length_between_ep_and_album/
        if len(self.song_collection) < 9:
            self.album_type = AlbumType.EP
            return

    def update_tracksort(self):
        """
        This updates the tracksort attributes, of the songs in
        `self.song_collection`, and sorts the songs, if possible.

        It is advised to only call this function, once all the tracks are
        added to the songs.

        :return:
        """

        if self.song_collection.empty:
            return

        tracksort_map: Dict[int, Song] = {
            song.tracksort: song for song in self.song_collection if song.tracksort != 0
        }


        existing_list = self.song_collection.shallow_list
        for i in range(1, len(existing_list) + 1):
            if i not in tracksort_map:
                tracksort_map[i] = existing_list.pop(0)
                tracksort_map[i].tracksort = i

    def fix_artist_collection(self):
        """
        I add artists, that could only be feature artists to the feature artist collection.
        They get automatically moved to main artist collection, if a matching artist exists in the main artist collection or is appended to it later on.
        If I am not sure for any artist, I try to analyze the most common artist in the song collection of one album.
        """

        # move all artists that are in all feature_artist_collections, of every song, to the artist_collection
        pass

    @property
    def copyright(self) -> str:
        if self.date is None:
            return ""
        if self.date.has_year or len(self.label_collection) == 0:
            return ""

        return f"{self.date.year} {self.label_collection[0].name}"

    @property
    def iso_639_2_lang(self) -> Optional[str]:
        if self.language is None:
            return None

        return self.language.alpha_3

    @property
    def is_split(self) -> bool:
        """
        A split Album is an Album from more than one Artists
        usually half the songs are made by one Artist, the other half by the other one.
        In this case split means either that or one artist featured by all songs.
        :return:
        """
        return len(self.artist_collection) > 1

    @property
    def album_type_string(self) -> str:
        return self.album_type.value


class Artist(Base):
    name: str
    country: Country
    formed_in: ID3Timestamp
    notes: FormattedText
    lyrical_themes: List[str]

    general_genre: str
    unformatted_location: str

    source_collection: SourceCollection
    contact_collection: Collection[Contact]

    album_collection: Collection[Album]
    label_collection: Collection[Label]

    _default_factories = {
        "name": lambda: None,
        "country": lambda: None,
        "unformatted_location": lambda: None,

        "formed_in": ID3Timestamp,
        "notes": FormattedText,
        "lyrical_themes": list,
        "general_genre": lambda: "",

        "source_collection": SourceCollection,
        "album_collection": Collection,
        "contact_collection": Collection,
        "label_collection": Collection,
    }

    TITEL = "name"

    # This is automatically generated
    def __init__(
        self, 
        name: str = None, 
        unified_name: str = None, 
        country: Country = None,
        formed_in: ID3Timestamp = None, 
        notes: FormattedText = None, 
        lyrical_themes: List[str] = None,
        general_genre: str = None, 
        unformatted_location: str = None, 
        source_list: List[Source] = None,
        contact_list: List[Contact] = None, 
        feature_song_list: List[Song] = None,
        album_list: List[Album] = None, 
        label_list: List[Label] = None, 
        **kwargs
    ) -> None:
        real_kwargs = copy.copy(locals())
        real_kwargs.update(real_kwargs.pop("kwargs", {}))

        Base.__init__(**real_kwargs)


    DOWNWARDS_COLLECTION_STRING_ATTRIBUTES = ("album_collection",)
    UPWARDS_COLLECTION_STRING_ATTRIBUTES = ("label_collection",)

    def __init_collections__(self):
        self.album_collection.append_object_to_attribute = {
            "feature_artist_collection": self
        }

        self.label_collection.append_object_to_attribute = {
            "current_artist_collection": self
        }

    def _add_other_db_objects(self, object_type: Type[OuterProxy], object_list: List[OuterProxy]):
        if object_type is Song:
            # this doesn't really make sense
            return

        if object_type is Artist:
            return

        if object_type is Album:
            self.album_collection.extend(object_list)
            return

        if object_type is Label:
            self.label_collection.extend(object_list)
            return

    def _compile(self):
        self.update_albumsort()

    def update_albumsort(self):
        """
        This updates the albumsort attributes, of the albums in
        `self.album_collection`, and sorts the albums, if possible.

        It is advised to only call this function, once all the albums are
        added to the artist.

        :return:
        """
        type_section: Dict[AlbumType, int] = defaultdict(lambda: 2, {
            AlbumType.OTHER: 0,  # if I don't know it, I add it to the first section
            AlbumType.STUDIO_ALBUM: 0,
            AlbumType.EP: 0,
            AlbumType.SINGLE: 1
        }) if main_settings["sort_album_by_type"] else defaultdict(lambda: 0)

        sections = defaultdict(list)

        # order albums in the previously defined section
        album: Album
        for album in self.album_collection:
            sections[type_section[album.album_type]].append(album)

        def sort_section(_section: List[Album], last_albumsort: int) -> int:
            # album is just a value used in loops
            nonlocal album

            if main_settings["sort_by_date"]:
                _section.sort(key=lambda _album: _album.date, reverse=True)

            new_last_albumsort = last_albumsort

            for album_index, album in enumerate(_section):
                if album.albumsort is None:
                    album.albumsort = new_last_albumsort = album_index + 1 + last_albumsort

            _section.sort(key=lambda _album: _album.albumsort)

            return new_last_albumsort

        # sort the sections individually
        _last_albumsort = 1
        for section_index in sorted(sections):
            _last_albumsort = sort_section(sections[section_index], _last_albumsort)

        # merge all sections again
        album_list = []
        for section_index in sorted(sections):
            album_list.extend(sections[section_index])

        # replace the old collection with the new one
        self.album_collection._data = album_list

    INDEX_DEPENDS_ON = ("name", "source_collection", "contact_collection")
    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('name', unify(self.name)),
            *[('contact', contact.value) for contact in self.contact_collection],
            *self.source_collection.indexing_values(),
        ]

    @property
    def metadata(self) -> Metadata:
        metadata = Metadata({
            id3Mapping.ARTIST: [self.name],
            id3Mapping.ARTIST_WEBPAGE_URL: self.source_collection.url_list,
        })

        return metadata

    @property
    def option_string(self) -> str:
        r = "artist "
        r += OPTION_FOREGROUND.value + self.title_string + BColors.ENDC.value + OPTION_BACKGROUND.value
        r += get_collection_string(self.label_collection, " under {}")
        
        r += OPTION_BACKGROUND.value
        if len(self.album_collection) > 0:
            r += f" with {len(self.album_collection)} albums"
        
        r += BColors.ENDC.value

        return r


class Label(Base):
    COLLECTION_STRING_ATTRIBUTES = ("album_collection", "current_artist_collection")

    DOWNWARDS_COLLECTION_STRING_ATTRIBUTES = COLLECTION_STRING_ATTRIBUTES

    name: str
    unified_name: str
    notes: FormattedText

    source_collection: SourceCollection
    contact_collection: Collection[Contact]

    album_collection: Collection[Album]
    current_artist_collection: Collection[Artist]

    _default_factories = {
        "notes": FormattedText,
        "album_collection": Collection,
        "current_artist_collection": Collection,
        "source_collection": SourceCollection,
        "contact_collection": Collection,
        "name": lambda: None,
        "unified_name": lambda: None,
    }

    TITEL = "name"

    def __init__(
        self, 
        name: str = None, 
        unified_name: str = None, 
        notes: FormattedText = None,
        source_list: List[Source] = None, 
        contact_list: List[Contact] = None,
        album_list: List[Album] = None, 
        current_artist_list: List[Artist] = None, 
        **kwargs
    ) -> None:
        real_kwargs = copy.copy(locals())
        real_kwargs.update(real_kwargs.pop("kwargs", {}))

        Base.__init__(**real_kwargs)

    def __init_collections__(self):
        self.album_collection.append_object_to_attribute = {
            "label_collection": self
        }

        self.current_artist_collection.append_object_to_attribute = {
            "label_collection": self
        }

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('name', unify(self.name)),
            *[('url', source.url) for source in self.source_collection]
        ]

    def _add_other_db_objects(self, object_type: Type[OuterProxy], object_list: List[OuterProxy]):
        if object_type is Song:
            return

        if object_type is Artist:
            self.current_artist_collection.extend(object_list)
            return

        if object_type is Album:
            self.album_collection.extend(object_list)
            return

    @property
    def options(self) -> List[P]:
        options = [self]
        options.extend(self.current_artist_collection.shallow_list)
        options.extend(self.album_collection.shallow_list)

        return options

    @property
    def option_string(self):
        return "label " + OPTION_FOREGROUND.value + self.name + BColors.ENDC.value
