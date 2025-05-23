from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Type, Union, Generator, Dict, Any
from urllib.parse import urlparse

import pycountry
import musicbrainzngs
from bs4 import BeautifulSoup

from ..connection import Connection
from .abstract import Page
from ..utils.enums import SourceType, ALL_SOURCE_TYPES
from ..utils.enums.album import AlbumType, AlbumStatus
from ..objects import (
    Artist,
    Source,
    Song,
    Album,
    ID3Timestamp,
    FormattedText,
    Label,
    Target,
    DatabaseObject,
    Lyrics,
    Artwork
)
from ..utils.config import logging_settings, main_settings
from ..utils import string_processing, shared
from ..utils.string_processing import clean_song_title
from ..utils.support_classes.query import Query
from ..utils.support_classes.download_result import DownloadResult



class Musicbrainz(Page):
    SOURCE_TYPE = ALL_SOURCE_TYPES.MUSICBRAINZ

    HOST = "https://musicbrainz.org"

    def __init__(self, *args, **kwargs):
        musicbrainzngs.set_useragent("mk", "1")

        super().__init__(*args, **kwargs)
    
    def general_search(self, search_query: str) -> List[DatabaseObject]:
        search_results = []

        #Artist
        search_results += self.artist_search(search_query).copy()

        #Album
        search_results += self.album_search(search_query).copy()

        #Song
        search_results += self.song_search(search_query).copy()

        return search_results

    def artist_search(self, search_query: str) -> List[Artist]:
        artist_list = []
        
        #Artist
        artist_dict_list: list = musicbrainzngs.search_artists(search_query)['artist-list']
        artist_source_list: List[Source] = []
        for artist_dict in artist_dict_list:
            artist_source_list.append(Source(self.SOURCE_TYPE, self.HOST + "/artist/" + artist_dict['id']))
            artist_list.append(Artist(
                name=artist_dict['name'],
                source_list=artist_source_list
            ))
  
        return artist_list

    def song_search(self, search_query: str) -> List[Song]:
        song_list = []

        #Song
        song_dict_list: list = musicbrainzngs.search_recordings(search_query)['recording-list']
        song_source_list: List[Source] = [] 
        for song_dict in song_dict_list:
            song_source_list.append(Source(self.SOURCE_TYPE, self.HOST + "/recording/" + song_dict['id'])) 
            song_list.append(Song(
                title=song_dict['title'],
                source_list=song_source_list
            )) 

        return song_list
    
    def album_search(self, search_query: str) -> List[Album]:
        album_list = []

        #Album
        album_dict_list: list = musicbrainzngs.search_release_groups(search_query)['release-group-list']
        album_source_list: List[Source] = []
        for album_dict in album_dict_list:
            album_source_list.append(Source(self.SOURCE_TYPE, self.HOST + "/release-group/" + album_dict['id']))
            album_list.append(Album(
                title=album_dict['title'],
                source_list=album_source_list
            ))

        return album_list


    def fetch_album(self, source: Source, stop_at_level: int = 1) -> Album:
        album_list = []

        #Album
        album_dict_list: list = musicbrainzngs.search_release_groups(search_query)['release-group-list']
        album_source_list: List[Source] = []
        for album_dict in album_dict_list:
            album_source_list.append(Source(self.SOURCE_TYPE, self.HOST + "/release-group/" + album_dict['id']))
            album_list.append(Album(
                title=album_dict['title'],
                source_list=album_source_list
            ))

    def fetch_artist(self, source: Source, stop_at_level: int = 1) -> Artist:
        artist_list = []
        
        #Artist
        artist_dict_list: list = musicbrainzngs.search_artists(search_query)['artist-list']
        artist_source_list: List[Source] = []
        for artist_dict in artist_dict_list:
            artist_source_list.append(Source(self.SOURCE_TYPE, self.HOST + "/artist/" + artist_dict['id']))
            artist_list.append(Artist(
                name=artist_dict['name'],
                source_list=artist_source_list,
            ))

    def fetch_song(self, source: Source, stop_at_level: int = 1) -> Song:
        song_list = []

        #Song
        song_dict_list: list = musicbrainzngs.search_recordings(search_query)['recording-list']
        song_source_list: List[Source] = [] 
        for song_dict in song_dict_list:
            song_source_list.append(Source(self.SOURCE_TYPE, self.HOST + "/recording/" + song_dict['id'])) 
            song_list.append(Song(
                title=song_dict['title'],
                source_list=song_source_list
            )) 
    
        