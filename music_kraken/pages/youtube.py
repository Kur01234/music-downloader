from typing import List, Optional, Type, Tuple
from urllib.parse import urlparse, urlunparse, parse_qs
from enum import Enum

import python_sponsorblock

from ..objects import Source, DatabaseObject, Song, Target
from .abstract import Page
from ..objects import (
    Artist,
    Source,
    Song,
    Album,
    Label,
    Target,
    FormattedText,
    ID3Timestamp
)
from ..connection import Connection
from ..utils.string_processing import clean_song_title
from ..utils.enums import SourceType, ALL_SOURCE_TYPES
from ..utils.support_classes.download_result import DownloadResult
from ..utils.config import youtube_settings, main_settings, logging_settings

from .youtube_music.super_youtube import SuperYouTube, YouTubeUrl, get_invidious_url, YouTubeUrlType


"""
- https://yt.artemislena.eu/api/v1/search?q=Zombiez+-+Topic&page=1&date=none&type=channel&duration=none&sort=relevance
- https://yt.artemislena.eu/api/v1/channels/playlists/UCV0Ntl3lVR7xDXKoCU6uUXA
- https://yt.artemislena.eu/api/v1/playlists/OLAK5uy_kcUBiDv5ATbl-R20OjNaZ5G28XFanQOmM
- https://yt.artemislena.eu/api/v1/videos/SULFl39UjgY
"""


def get_piped_url(path: str = "", params: str = "", query: str = "", fragment: str = "") -> str:
    return urlunparse((youtube_settings["piped_instance"].scheme, youtube_settings["piped_instance"].netloc, path, params, query, fragment))


class YouTube(SuperYouTube):
    # CHANGE
    SOURCE_TYPE = ALL_SOURCE_TYPES.YOUTUBE

    def __init__(self, *args, **kwargs):
        self.connection: Connection = Connection(
            host=get_invidious_url(),
            logger=self.LOGGER
        )
        
        self.piped_connection: Connection = Connection(
            host=get_piped_url(),
            logger=self.LOGGER
        )

        self.download_connection: Connection = Connection(
            host="https://www.youtube.com/",
            logger=self.LOGGER,
            sleep_after_404=youtube_settings["sleep_after_youtube_403"]
        )
        
        # the stuff with the connection is, to ensure sponsorblock uses the proxies, my programm does
        _sponsorblock_connection: Connection = Connection()
        self.sponsorblock = python_sponsorblock.SponsorBlock(silent=True, session=_sponsorblock_connection.session)


        super().__init__(*args, **kwargs)

    def general_search(self, search_query: str) -> List[DatabaseObject]:
        return self.artist_search(Artist(name=search_query, dynamic=True))
    
    def _json_to_artist(self, artist_json: dict) -> Artist:#
        return Artist(
            name=artist_json["author"].replace(" - Topic", ""),
            source_list=[
                Source(self.SOURCE_TYPE, get_invidious_url(path=artist_json["authorUrl"]))
            ]
        )

    def artist_search(self, artist: Artist) -> List[Artist]:
        # https://yt.artemislena.eu/api/v1/search?q=Zombiez+-+Topic&page=1&date=none&type=channel&duration=none&sort=relevance
        endpoint = get_invidious_url(path="/api/v1/search", query=f"q={artist.name.replace(' ', '+')}+-+Topic&page=1&date=none&type=channel&duration=none&sort=relevance")
        
        artist_list = []
        
        r = self.connection.get(endpoint)
        if r is None:
            return []

        for search_result in r.json():
            if search_result["type"] != "channel":
                continue
            author: str = search_result["author"]
            if not author.endswith(" - Topic"):
                continue
            
            artist_list.append(self._json_to_artist(search_result))
            
        return artist_list

    def _fetch_song_from_id(self, youtube_id: str) -> Tuple[Song, Optional[int]]:
        # https://yt.artemislena.eu/api/v1/videos/SULFl39UjgY
        r = self.connection.get(get_invidious_url(path=f"/api/v1/videos/{youtube_id}"))
        if r is None:
            return Song(), None

        data = r.json()
        if data["genre"] != "Music":
            self.LOGGER.warning(f"Genre has to be music, trying anyways")

        title = data["title"]
        license_str = None

        artist_list: List[Artist] = []

        _author: str = data["author"]
        if _author.endswith(" - Topic"):
            artist_list.append(Artist(
                name=_author.replace(" - Topic", ""),
                source_list=[Source(
                    self.SOURCE_TYPE, get_invidious_url(path=f"/channel/{data['authorId']}")
                )]
            ))

        else:
            # If the song is not a topic song in the beginning, it cleans the title. If it is from a topic channel, it is clean anyways
            # If cleaned data is returned by the api, it will be overridden in the next step anyways
            title = clean_song_title(title, _author)

            for music_track in data.get("musicTracks", []):
                title = music_track["song"]
                license_str = music_track["license"]

                for artist_name in music_track["artist"].split(" x "):
                    artist_list.append(Artist(name=artist_name))

        # if all attempts to get a clean artis name (mainly striping topic or getting the stuff in the api) fail, just add an artist with the name of the uploader channel
        if len(artist_list) == 0:
            artist_list.append(Artist(name=_author))

        return Song(
            title=title,
            source_list=[Source(
                self.SOURCE_TYPE, get_invidious_url(path="/watch", query=f"v={data['videoId']}")
            )],
            notes=FormattedText(html=data["descriptionHtml"] + f"\n<p>{license_str}</ p>" ),
            artist_list=artist_list
        ), int(data["published"])

    def fetch_song(self, source: Source, stop_at_level: int = 1) -> Song:
        parsed = YouTubeUrl(source.url)
        if parsed.url_type != YouTubeUrlType.VIDEO:
            return Song()

        song, _ = self._fetch_song_from_id(parsed.id)
        return song

    def fetch_album(self, source: Source, stop_at_level: int = 1) -> Album:
        self.LOGGER.info(f"Getting the metadata of an album may take slightly longer, only panic in a couple minutes <333")
        
        parsed = YouTubeUrl(source.url)
        if parsed.url_type != YouTubeUrlType.PLAYLIST:
            return Album()

        title = None
        source_list = [source]
        notes = None
        song_list = []

        # https://yt.artemislena.eu/api/v1/playlists/OLAK5uy_kcUBiDv5ATbl-R20OjNaZ5G28XFanQOmM
        r = self.connection.get(get_invidious_url(path=f"/api/v1/playlists/{parsed.id}"))
        if r is None:
            return Album()

        data = r.json()
        if data["type"] != "playlist":
            return Album()

        title = data["title"]
        notes = FormattedText(html=data["descriptionHtml"])

        timestamps: List[int] = []

        """
        TODO
        fetch the song and don't get it from there
        """
        for video in data["videos"]:
            other_song = Song(
                source_list=[
                    Source(
                        self.SOURCE_TYPE, get_invidious_url(path="/watch", query=f"v={video['videoId']}")
                    )
                ],
                tracksort=video["index"]+1
            )

            song, utc_timestamp = self._fetch_song_from_id(video["videoId"])
            song.merge(other_song)

            if utc_timestamp is not None:
                timestamps.append(utc_timestamp)
            song_list.append(song)

        return Album(
            title=title,
            source_list=source_list,
            notes=notes,
            song_list=song_list,
            date=ID3Timestamp.fromtimestamp(round(sum(timestamps) / len(timestamps)))
        )

    def fetch_invidious_album_list(self, yt_id: str):
        artist_name = None
        album_list = []
        
        # playlist
        # https://yt.artemislena.eu/api/v1/channels/playlists/UCV0Ntl3lVR7xDXKoCU6uUXA
        r = self.connection.get(get_invidious_url(f"/api/v1/channels/playlists/{yt_id}"))
        if r is None:
            return Artist()

        for playlist_json in r.json()["playlists"]:
            if playlist_json["type"] != "playlist":
                continue
            
            artist_name = playlist_json["author"].replace(" - Topic", "")
            
            # /playlist?list=OLAK5uy_nbvQeskr8nbIuzeLxoceNLuCL_KjAmzVw
            album_list.append(Album(
                title=playlist_json["title"],
                source_list=[Source(
                    self.SOURCE_TYPE, get_invidious_url(path="/playlist", query=f"list={playlist_json['playlistId']}")
                )],
                artist_list=[Artist(
                    name=artist_name,
                    source_list=[
                        Source(self.SOURCE_TYPE, get_invidious_url(path=playlist_json["authorUrl"]))
                    ]
                )]
            ))
        
        return album_list, artist_name

    def fetch_piped_album_list(self, yt_id: str):
        endpoint = get_piped_url(path=f"/channels/tabs", query='data={"originalUrl":"https://www.youtube.com/' + yt_id + '/playlists","url":"https://www.youtube.com/' + yt_id + 'playlists","id":"' + yt_id + '","contentFilters":["playlists"],"sortFilter":"","baseUrl":"https://www.youtube.com"}')
        
        r = self.piped_connection.get(endpoint)
        if r is None:
            return [], None
        
        content = r.json()["content"]
        
        artist_name = None
        album_list = []
        
        for playlist in content:
            if playlist["type"] != "playlist":
                continue
            
            artist_name = playlist["uploaderName"].replace(" - Topic", "")
            
            album_list.append(Album(
                title=playlist["name"],
                source_list=[Source(
                    self.SOURCE_TYPE, get_invidious_url() + playlist["url"]
                )],
                artist_list=[Artist(
                    name=artist_name,
                    source_list=[
                        Source(self.SOURCE_TYPE, get_invidious_url(path=playlist["uploaderUrl"]))
                    ]
                )]
            ))
        
        return album_list, artist_name

    def fetch_artist(self, source: Source, stop_at_level: int = 1) -> Artist:
        parsed = YouTubeUrl(source.url)
        if parsed.url_type != YouTubeUrlType.CHANNEL:
            return Artist(source_list=[source])
        
        album_list, artist_name  = self.fetch_piped_album_list(parsed.id)
        if len(album_list) <= 0:
            self.LOGGER.warning(f"didn't found any playlists with piped, falling back to invidious. (it is unusual)")
            album_list, artist_name = self.fetch_invidious_album_list(parsed.id)
        
        return Artist(name=artist_name, album_list=album_list, source_list=[source])

    def download_song_to_target(self, source: Source, target: Target, desc: str = None) -> DownloadResult:
        """
        1. getting the optimal source
        Only audio sources allowed
        not a bitrate that is smaller than the selected bitrate, but not one that is wayyy huger

        2. download it

        :param source:
        :param target:
        :param desc:
        :return:
        """
        r = self.connection.get(YouTubeUrl(source.url).api)
        if r is None:
            return DownloadResult(error_message="Api didn't even respond, maybe try another invidious Instance")

        audio_format = None
        best_bitrate = 0

        for possible_format in r.json()["adaptiveFormats"]:
            format_type: str = possible_format["type"]
            if not format_type.startswith("audio"):
                continue

            bitrate = int(possible_format.get("bitrate", 0))

            if bitrate >= main_settings["bitrate"]:
                best_bitrate = bitrate
                audio_format = possible_format
                break

            if bitrate > best_bitrate:
                best_bitrate = bitrate
                audio_format = possible_format

        if audio_format is None:
            return DownloadResult(error_message="Couldn't find the download link.")

        endpoint = audio_format["url"]

        return self.download_connection.stream_into(endpoint, target, description=desc, raw_url=True)


    def get_skip_intervals(self, song: Song, source: Source) -> List[Tuple[float, float]]:
        if not youtube_settings["use_sponsor_block"]:
            return []
        
        parsed = YouTubeUrl(source.url)
        if parsed.url_type != YouTubeUrlType.VIDEO:
            self.LOGGER.warning(f"{source.url} is no video url.")
            return []
        
        segments = []
        try:
            segments = self.sponsorblock.get_segments(parsed.id)
        except NotFoundException:
            self.LOGGER.debug(f"No sponsor found for the video {parsed.id}.")
        except HTTPException as e:
            self.LOGGER.warning(f"{e}")

        return [(segment.segment[0], segment.segment[1]) for segment in segments]
