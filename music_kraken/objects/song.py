from __future__ import annotations

import random
from collections import defaultdict
from typing import List, Optional, Dict, Tuple, Type, Union

import pycountry

from ..utils.enums.album import AlbumType, AlbumStatus
from .collection import Collection
from .formatted_text import FormattedText
from .lyrics import Lyrics
from .contact import Contact
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
from ..utils.string_processing import unify

from .parents import OuterProxy as Base

from ..utils.config import main_settings

"""
All Objects dependent 
"""

CountryTyping = type(list(pycountry.countries)[0])
OPTION_STRING_DELIMITER = " | "


class Song(Base):
    title: str
    unified_title: str
    isrc: str
    length: int
    genre: str
    note: FormattedText
    tracksort: int

    source_collection: SourceCollection
    target_collection: Collection[Target]
    lyrics_collection: Collection[Lyrics]
    main_artist_collection: Collection[Artist]
    feature_artist_collection: Collection[Artist]
    album_collection: Collection[Album]

    _default_factories = {
        "note": FormattedText,
        "length": lambda: 0,
        "source_collection": SourceCollection,
        "target_collection": Collection,
        "lyrics_collection": Collection,

        "main_artist_collection": Collection,
        "album_collection": Collection,
        "feature_artist_collection": Collection,

        "title": lambda: "",
        "unified_title": lambda: None,
        "isrc": lambda: None,
        "genre": lambda: None,

        "tracksort": lambda: 0,
    }

    def __init__(self, title: str = "", unified_title: str = None, isrc: str = None, length: int = None,
                 genre: str = None, note: FormattedText = None, source_list: List[Source] = None,
                 target_list: List[Target] = None, lyrics_list: List[Lyrics] = None,
                 main_artist_list: List[Artist] = None, feature_artist_list: List[Artist] = None,
                 album_list: List[Album] = None, tracksort: int = 0, **kwargs) -> None:

        Base.__init__(**locals())

    UPWARDS_COLLECTION_STRING_ATTRIBUTES = ("album_collection", "main_artist_collection", "feature_artist_collection")

    def __init_collections__(self) -> None:
        self.album_collection.contain_given_in_attribute = {
            "artist_collection": self.main_artist_collection,
        }
        self.album_collection.append_object_to_attribute = {
            "song_collection": self,
        }

        self.main_artist_collection.contain_given_in_attribute = {
            "main_album_collection": self.album_collection
        }
        self.feature_artist_collection.append_object_to_attribute = {
            "feature_song_collection": self
        }

    def _add_other_db_objects(self, object_type: Type[OuterProxy], object_list: List[OuterProxy]):
        if object_type is Song:
            return

        if isinstance(object_list, Lyrics):
            self.lyrics_collection.extend(object_list)
            return

        if isinstance(object_list, Artist):
            self.main_artist_collection.extend(object_list)
            return

        if isinstance(object_list, Album):
            self.album_collection.extend(object_list)
            return

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('id', self.id),
            ('title', self.unified_title),
            ('isrc', self.isrc),
            *[('url', source.url) for source in self.source_collection]
        ]

    @property
    def metadata(self) -> Metadata:
        metadata = Metadata({
            id3Mapping.TITLE: [self.title],
            id3Mapping.ISRC: [self.isrc],
            id3Mapping.LENGTH: [self.length],
            id3Mapping.GENRE: [self.genre],
            id3Mapping.TRACKNUMBER: [self.tracksort_str]
        })

        # metadata.merge_many([s.get_song_metadata() for s in self.source_collection])  album sources have no relevant metadata for id3
        metadata.merge_many([a.metadata for a in self.album_collection])
        metadata.merge_many([a.metadata for a in self.main_artist_collection])
        metadata.merge_many([a.metadata for a in self.feature_artist_collection])
        metadata.merge_many([lyrics.metadata for lyrics in self.lyrics_collection])

        return metadata

    def get_artist_credits(self) -> str:
        main_artists = ", ".join([artist.name for artist in self.main_artist_collection])
        feature_artists = ", ".join([artist.name for artist in self.feature_artist_collection])

        if len(feature_artists) == 0:
            return main_artists
        return f"{main_artists} feat. {feature_artists}"

    """
    def __str__(self) -> str:
        artist_credit_str = ""
        artist_credits = self.get_artist_credits()
        if artist_credits != "":
            artist_credit_str = f" by {artist_credits}"

        return f"\"{self.title}\"{artist_credit_str}"
    """

    def __repr__(self) -> str:
        return f"Song(\"{self.title}\")"

    @property
    def option_string(self) -> str:
        return f"{self.__repr__()} " \
               f"from Album({OPTION_STRING_DELIMITER.join(album.title for album in self.album_collection)}) " \
               f"by Artist({OPTION_STRING_DELIMITER.join(artist.name for artist in self.main_artist_collection)}) " \
               f"feat. Artist({OPTION_STRING_DELIMITER.join(artist.name for artist in self.feature_artist_collection)})"

    @property
    def options(self) -> List[P]:
        options = self.main_artist_collection.shallow_list
        options.extend(self.feature_artist_collection)
        options.extend(self.album_collection)
        options.append(self)
        return options

    @property
    def tracksort_str(self) -> str:
        """
        if the album tracklist is empty, it sets it length to 1, this song has to be on the Album
        :returns id3_tracksort: {song_position}/{album.length_of_tracklist} 
        """
        if len(self.album_collection) == 0:
            return f"{self.tracksort}"

        return f"{self.tracksort}/{len(self.album_collection[0].song_collection) or 1}"


"""
All objects dependent on Album
"""


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
    artist_collection: Collection[Artist]
    song_collection: Collection[Song]
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
        "artist_collection": Collection,
        "song_collection": Collection,
        "label_collection": Collection,

    }

    # This is automatically generated
    def __init__(self, title: str = None, unified_title: str = None, album_status: AlbumStatus = None,
                 album_type: AlbumType = None, language: Language = None, date: ID3Timestamp = None,
                 barcode: str = None, albumsort: int = None, notes: FormattedText = None,
                 source_list: List[Source] = None, artist_list: List[Artist] = None, song_list: List[Song] = None,
                 label_list: List[Label] = None, **kwargs) -> None:
        super().__init__(title=title, unified_title=unified_title, album_status=album_status, album_type=album_type,
                         language=language, date=date, barcode=barcode, albumsort=albumsort, notes=notes,
                         source_list=source_list, artist_list=artist_list, song_list=song_list, label_list=label_list,
                         **kwargs)

    DOWNWARDS_COLLECTION_STRING_ATTRIBUTES = ("song_collection",)
    UPWARDS_COLLECTION_STRING_ATTRIBUTES = ("artist_collection", "label_collection")

    def __init_collections__(self):
        self.song_collection.contain_attribute_in_given = {
            "main_artist_collection": self.artist_collection
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

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('id', self.id),
            ('title', self.unified_title),
            ('barcode', self.barcode),
            *[('url', source.url) for source in self.source_collection]
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

    def __repr__(self):
        return f"Album(\"{self.title}\")"

    @property
    def option_string(self) -> str:
        return f"{self.__repr__()} " \
               f"by Artist({OPTION_STRING_DELIMITER.join([artist.name for artist in self.artist_collection])}) " \
               f"under Label({OPTION_STRING_DELIMITER.join([label.name for label in self.label_collection])})"

    @property
    def options(self) -> List[P]:
        options = [*self.artist_collection, self, *self.song_collection]

        return options

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
            song.tracksort: song for song in self.song_collection if song.tracksort is not None
        }

        # place the songs, with set tracksort attribute according to it
        for tracksort, song in tracksort_map.items():
            index = tracksort - 1

            """
            I ONLY modify the `Collection._data` attribute directly, 
            to bypass the mapping of the attributes, because I will add the item in the next step
            """

            """
            but for some reason, neither 
            `self.song_collection._data.index(song)`
            `self.song_collection._data.remove(song)`
            get the right object.
            
            I have NO FUCKING CLUE why xD
            But I just implemented it myself.
            """
            for old_index, temp_song in enumerate(self.song_collection._data):
                if song is temp_song:
                    break

            # the list can't be empty
            del self.song_collection._data[old_index]
            self.song_collection._data.insert(index, song)

        # fill in the empty tracksort attributes
        for i, song in enumerate(self.song_collection):
            if song.tracksort is not None:
                continue
            song.tracksort = i + 1

    def compile(self, merge_into: bool = False):
        """
        compiles the recursive structures,
        and does depending on the object some other stuff.

        no need to override if only the recursive structure should be built.
        override self.build_recursive_structures() instead
        """

        self.update_tracksort()
        self._build_recursive_structures(build_version=random.randint(0, 99999), merge=merge_into)

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


"""
All objects dependent on Artist
"""


class Artist(Base):
    name: str
    unified_name: str
    country: Country
    formed_in: ID3Timestamp
    notes: FormattedText
    lyrical_themes: List[str]

    general_genre: str
    unformated_location: str

    source_collection: SourceCollection
    contact_collection: Collection[Contact]

    feature_song_collection: Collection[Song]
    main_album_collection: Collection[Album]
    label_collection: Collection[Label]

    _default_factories = {
        "name": str,
        "unified_name": lambda: None,
        "country": lambda: None,
        "unformated_location": lambda: None,

        "formed_in": ID3Timestamp,
        "notes": FormattedText,
        "lyrical_themes": list,
        "general_genre": lambda: "",

        "source_collection": SourceCollection,
        "feature_song_collection": Collection,
        "main_album_collection": Collection,
        "contact_collection": Collection,
        "label_collection": Collection,
    }

    # This is automatically generated
    def __init__(self, name: str = "", unified_name: str = None, country: Country = None,
                 formed_in: ID3Timestamp = None, notes: FormattedText = None, lyrical_themes: List[str] = None,
                 general_genre: str = None, unformated_location: str = None, source_list: List[Source] = None,
                 contact_list: List[Contact] = None, feature_song_list: List[Song] = None,
                 main_album_list: List[Album] = None, label_list: List[Label] = None, **kwargs) -> None:

        super().__init__(name=name, unified_name=unified_name, country=country, formed_in=formed_in, notes=notes,
                         lyrical_themes=lyrical_themes, general_genre=general_genre,
                         unformated_location=unformated_location, source_list=source_list, contact_list=contact_list,
                         feature_song_list=feature_song_list, main_album_list=main_album_list, label_list=label_list,
                         **kwargs)

    DOWNWARDS_COLLECTION_STRING_ATTRIBUTES = ("feature_song_collection", "main_album_collection")
    UPWARDS_COLLECTION_STRING_ATTRIBUTES = ("label_collection",)

    def __init_collections__(self):
        self.feature_song_collection.append_object_to_attribute = {
            "feature_artist_collection": self
        }

        self.main_album_collection.append_object_to_attribute = {
            "artist_collection": self
        }

        self.label_collection.append_object_to_attribute = {
            "current_artist_collection": self
        }

    def _add_other_db_objects(self, object_type: Type[OuterProxy], object_list: List[OuterProxy]):
        if object_type is Song:
            # this doesn't really make sense
            # self.feature_song_collection.extend(object_list)
            return

        if object_type is Artist:
            return

        if object_type is Album:
            self.main_album_collection.extend(object_list)
            return

        if object_type is Label:
            self.label_collection.extend(object_list)
            return

    @property
    def options(self) -> List[P]:
        options = [self, *self.main_album_collection.shallow_list, *self.feature_album]
        print(options)
        return options

    def update_albumsort(self):
        """
        This updates the albumsort attributes, of the albums in
        `self.main_album_collection`, and sorts the albums, if possible.

        It is advised to only call this function, once all the albums are
        added to the artist.

        :return:
        """
        if len(self.main_album_collection) <= 0:
            return

        type_section: Dict[AlbumType, int] = defaultdict(lambda: 2, {
            AlbumType.OTHER: 0,  # if I don't know it, I add it to the first section
            AlbumType.STUDIO_ALBUM: 0,
            AlbumType.EP: 0,
            AlbumType.SINGLE: 1
        }) if main_settings["sort_album_by_type"] else defaultdict(lambda: 0)

        sections = defaultdict(list)

        # order albums in the previously defined section
        album: Album
        for album in self.main_album_collection:
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
        self.main_album_collection: Collection = Collection(data=album_list, element_type=Album)

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('id', self.id),
            ('name', self.unified_name),
            *[('url', source.url) for source in self.source_collection],
            *[('contact', contact.value) for contact in self.contact_collection]
        ]

    @property
    def metadata(self) -> Metadata:
        metadata = Metadata({
            id3Mapping.ARTIST: [self.name]
        })
        metadata.merge_many([s.get_artist_metadata() for s in self.source_collection])

        return metadata

    """
    def __str__(self, include_notes: bool = False):
        string = self.name or ""
        if include_notes:
            plaintext_notes = self.notes.get_plaintext()
            if plaintext_notes is not None:
                string += "\n" + plaintext_notes
        return string
    """

    def __repr__(self):
        return f"Artist(\"{self.name}\")"

    @property
    def option_string(self) -> str:
        return f"{self.__repr__()} " \
               f"under Label({OPTION_STRING_DELIMITER.join([label.name for label in self.label_collection])})"

    @property
    def options(self) -> List[P]:
        options = [self]
        options.extend(self.main_album_collection)
        options.extend(self.feature_song_collection)
        return options

    @property
    def feature_album(self) -> Album:
        return Album(
            title="features",
            album_status=AlbumStatus.UNRELEASED,
            album_type=AlbumType.COMPILATION_ALBUM,
            is_split=True,
            albumsort=666,
            dynamic=True,
            song_list=self.feature_song_collection.shallow_list
        )

    def get_all_songs(self) -> List[Song]:
        """
        returns a list of all Songs.
        probably not that useful, because it is unsorted
        """
        collection = self.feature_song_collection.copy()
        for album in self.discography:
            collection.extend(album.song_collection)

        return collection

    @property
    def discography(self) -> List[Album]:
        flat_copy_discography = self.main_album_collection.copy()
        flat_copy_discography.append(self.feature_album)

        return flat_copy_discography


"""
Label
"""


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

    def __init__(self, name: str = None, unified_name: str = None, notes: FormattedText = None,
                 source_list: List[Source] = None, contact_list: List[Contact] = None,
                 album_list: List[Album] = None, current_artist_list: List[Artist] = None, **kwargs) -> None:
        super().__init__(name=name, unified_name=unified_name, notes=notes, source_list=source_list,
                         contact_list=contact_list, album_list=album_list, current_artist_list=current_artist_list,
                         **kwargs)

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('id', self.id),
            ('name', self.unified_name),
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
