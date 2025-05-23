from typing import List, Optional, Type
from urllib.parse import urlparse, urlunparse, urlencode
import json
from enum import Enum
from bs4 import BeautifulSoup
import pycountry

from ..objects import Source, DatabaseObject
from .abstract import Page
from ..objects import (
    Artist,
    Source,
    SourceType,
    Song,
    Album,
    Label,
    Target,
    Contact,
    ID3Timestamp,
    Lyrics,
    FormattedText,
    Artwork,
)
from ..connection import Connection
from ..utils import dump_to_file, traverse_json_path
from ..utils.enums import SourceType, ALL_SOURCE_TYPES
from ..utils.support_classes.download_result import DownloadResult
from ..utils.string_processing import clean_song_title
from ..utils.config import main_settings, logging_settings
from ..utils.shared import DEBUG

if DEBUG:
    from ..utils import dump_to_file


class Genius(Page):
    SOURCE_TYPE = ALL_SOURCE_TYPES.GENIUS
    HOST = "genius.com"

    def __init__(self, *args, **kwargs):
        self.connection: Connection = Connection(
            host="https://genius.com/",
            logger=self.LOGGER,
            module="genius",
        )

        super().__init__(*args, **kwargs)

    def get_source_type(self, source: Source) -> Optional[Type[DatabaseObject]]:
        path = source.parsed_url.path.replace("/", "")
        
        if path.startswith("artists"):
            return Artist
        if path.startswith("albums"):
            return Album

        return Song

    def add_to_artwork(self, artwork: Artwork, url: str):
        if url is None:
            return
        
        url_frags = url.split(".")
        if len(url_frags) < 2:
            artwork.append(url=url)
            return

        dimensions = url_frags[-2].split("x")
        if len(dimensions) < 2:
            artwork.append(url=url)
            return

        if len(dimensions) == 3:
            dimensions = dimensions[:-1]
        
        try:
            artwork.append(url=url, width=int(dimensions[0]), height=int(dimensions[1]))
        except ValueError:
            artwork.append(url=url)

    def parse_api_object(self, data: dict) -> Optional[DatabaseObject]:
        if data is None:
            return None
        object_type = data.get("_type")

        artwork = Artwork()
        self.add_to_artwork(artwork, data.get("header_image_url"))
        self.add_to_artwork(artwork, data.get("image_url"))
        
        additional_sources: List[Source] = []
        source: Source = Source(self.SOURCE_TYPE, data.get("url"), additional_data={
            "id": data.get("id"),
            "slug": data.get("slug"),
            "api_path": data.get("api_path"),
        })

        notes = FormattedText()
        description = data.get("description") or {}
        if "html" in description:
            notes.html = description["html"]
        elif "markdown" in description:
            notes.markdown = description["markdown"]
        elif "description_preview" in data:
            notes.plaintext = data["description_preview"]

        if source.url is None:
            return None

        if object_type == "artist":
            if data.get("instagram_name") is not None:
                additional_sources.append(Source(ALL_SOURCE_TYPES.INSTAGRAM, f"https://www.instagram.com/{data['instagram_name']}/"))
            if data.get("facebook_name") is not None:
                additional_sources.append(Source(ALL_SOURCE_TYPES.FACEBOOK, f"https://www.facebook.com/{data['facebook_name']}/"))
            if data.get("twitter_name") is not None:
                additional_sources.append(Source(ALL_SOURCE_TYPES.TWITTER, f"https://x.com/{data['twitter_name']}/"))

            return Artist(
                name=data["name"].strip() if data.get("name") is not None else None,
                source_list=[source],
                artwork=artwork,
                notes=notes,
            )

        if object_type == "album":
            self.add_to_artwork(artwork, data.get("cover_art_thumbnail_url"))
            self.add_to_artwork(artwork, data.get("cover_art_url"))

            for cover_art in data.get("cover_arts", []):
                self.add_to_artwork(artwork, cover_art.get("image_url"))
                self.add_to_artwork(artwork, cover_art.get("thumbnail_image_url"))

            return Album(
                title=data.get("name").strip(),
                source_list=[source],
                artist_list=[self.parse_api_object(data.get("artist"))],
                artwork=artwork,
                date=ID3Timestamp(**(data.get("release_date_components") or {})),
            )

        if object_type == "song":
            self.add_to_artwork(artwork, data.get("song_art_image_thumbnail_url"))
            self.add_to_artwork(artwork, data.get("song_art_image_url"))

            main_artist_list = []
            featured_artist_list = []

            _artist_name = None
            primary_artist = self.parse_api_object(data.get("primary_artist"))
            if primary_artist is not None:
                _artist_name = primary_artist.name
                main_artist_list.append(primary_artist)
            for feature_artist in (*(data.get("featured_artists") or []), *(data.get("producer_artists") or []), *(data.get("writer_artists") or [])):
                artist = self.parse_api_object(feature_artist)
                if artist is not None:
                    featured_artist_list.append(artist)

            return Song(
                title=clean_song_title(data.get("title"), artist_name=_artist_name),
                source_list=[source],
                artwork=artwork,
                feature_artist_list=featured_artist_list,
                artist_list=main_artist_list,
            )

        return None

    def general_search(self, search_query: str, **kwargs) -> List[DatabaseObject]:
        results = []

        search_params = {
            "q": search_query,
        }

        r = self.connection.get("https://genius.com/api/search/multi?" + urlencode(search_params), name=f"search_{search_query}")
        if r is None:
            return results

        dump_to_file("search_genius.json", r.text, is_json=True, exit_after_dump=False)
        data = r.json()

        for elements in traverse_json_path(data, "response.sections", default=[]):
            hits = elements.get("hits", [])
            for hit in hits:
                parsed = self.parse_api_object(hit.get("result"))
                if parsed is not None:
                    results.append(parsed)

        return results

    def fetch_artist(self, source: Source, stop_at_level: int = 1) -> Artist:
        artist: Artist = Artist()
        # https://genius.com/api/artists/24527/albums?page=1

        r = self.connection.get(source.url, name=source.url)
        if r is None:
            return artist
        soup = self.get_soup_from_response(r)

        # find the content attribute in the meta tag which is contained in the head
        data_container = soup.find("meta", {"itemprop": "page_data"})
        if data_container is not None:
            content = data_container["content"]
            dump_to_file("genius_itemprop_artist.json", content, is_json=True, exit_after_dump=False)
            data = json.loads(content)

            artist = self.parse_api_object(data.get("artist"))
            
            for e in (data.get("artist_albums") or []):
                r = self.parse_api_object(e)
                if not isinstance(r, Album):
                    continue

                artist.album_collection.append(r)
            
            for e in (data.get("artist_songs") or []):
                r = self.parse_api_object(e)
                if not isinstance(r, Song):
                    continue

                """
                TODO
                fetch the album for these songs, because the api doesn't 
                return them
                """

                artist.album_collection.extend(r.album_collection)

        artist.source_collection.append(source)

        return artist

    def fetch_album(self, source: Source, stop_at_level: int = 1) -> Album:
        album: Album = Album()
        # https://genius.com/api/artists/24527/albums?page=1

        r = self.connection.get(source.url, name=source.url)
        if r is None:
            return album
        soup = self.get_soup_from_response(r)

        # find the content attribute in the meta tag which is contained in the head
        data_container = soup.find("meta", {"itemprop": "page_data"})
        if data_container is not None:
            content = data_container["content"]
            dump_to_file("genius_itemprop_album.json", content, is_json=True, exit_after_dump=False)
            data = json.loads(content)

            album = self.parse_api_object(data.get("album"))

            for e in data.get("album_appearances", []):
                r = self.parse_api_object(e.get("song"))
                if not isinstance(r, Song):
                    continue

                album.song_collection.append(r)

        album.source_collection.append(source)
        
        return album

    def get_json_content_from_response(self, response, start: str, end: str) -> Optional[str]:
        content = response.text
        start_index = content.find(start)
        if start_index < 0:
            return None
        start_index += len(start)
        end_index = content.find(end, start_index)
        if end_index < 0:
            return None
        return content[start_index:end_index]

    def fetch_song(self, source: Source, stop_at_level: int = 1) -> Song:
        song: Song = Song()

        r = self.connection.get(source.url, name=source.url)
        if r is None:
            return song

        # get the contents that are between `JSON.parse('` and `');`
        content = self.get_json_content_from_response(r, start="window.__PRELOADED_STATE__ = JSON.parse('", end="');\n      window.__APP_CONFIG__ = ")
        if content is not None:
            content = content.replace("\\\\", "\\").replace('\\"', '"').replace("\\'", "'")
            data = json.loads(content)

            lyrics_html = traverse_json_path(data, "songPage.lyricsData.body.html", default=None)
            if lyrics_html is not None:
                song.lyrics_collection.append(Lyrics(FormattedText(html=lyrics_html)))

            dump_to_file("genius_song_script_json.json", content, is_json=True, exit_after_dump=False)

        soup = self.get_soup_from_response(r)
        for lyrics in soup.find_all("div", {"data-lyrics-container": "true"}):
            lyrics_object = Lyrics(FormattedText(html=lyrics.prettify()))
            song.lyrics_collection.append(lyrics_object)

        song.source_collection.append(source)
        return song
