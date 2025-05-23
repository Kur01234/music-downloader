from typing import List, Optional, Type, Tuple
from urllib.parse import urlparse, urlunparse, parse_qs
from enum import Enum
import requests

import python_sponsorblock

from ...objects import Source, DatabaseObject, Song, Target
from ..abstract import Page
from ...objects import (
    Artist,
    Source,
    Song,
    Album,
    Label,
    Target,
    FormattedText,
    ID3Timestamp
)
from ...connection import Connection
from ...utils.support_classes.download_result import DownloadResult
from ...utils.config import youtube_settings, logging_settings, main_settings
from ...utils.enums import SourceType, ALL_SOURCE_TYPES


def get_invidious_url(path: str = "", params: str = "", query: str = "", fragment: str = "") -> str:
    return urlunparse((youtube_settings["invidious_instance"].scheme, youtube_settings["invidious_instance"].netloc, path, params, query, fragment))


class YouTubeUrlType(Enum):
    CHANNEL = "channel"
    PLAYLIST = "playlist"
    VIDEO = "watch"
    NONE = ""


class YouTubeUrl:
    """
    Artist
    https://yt.artemislena.eu/channel/UCV0Ntl3lVR7xDXKoCU6uUXA
    https://www.youtube.com/channel/UCV0Ntl3lVR7xDXKoCU6uUXA
    
    Release
    https://yt.artemislena.eu/playlist?list=OLAK5uy_nEg5joAyFjHBPwnS_ADHYtgSqAjFMQKLw
    https://www.youtube.com/playlist?list=OLAK5uy_nEg5joAyFjHBPwnS_ADHYtgSqAjFMQKLw
    
    Track
    https://yt.artemislena.eu/watch?v=SULFl39UjgY&list=OLAK5uy_nEg5joAyFjHBPwnS_ADHYtgSqAjFMQKLw&index=1
    https://www.youtube.com/watch?v=SULFl39UjgY
    """
    
    def __init__(self, url: str) -> None:
        self.SOURCE_TYPE = ALL_SOURCE_TYPES.YOUTUBE

        """
        Raises Index exception for wrong url, and value error for not found enum type
        """
        self.id = ""
        parsed = urlparse(url=url)

        self.url_type: YouTubeUrlType
        
        type_frag_list = parsed.path.split("/")
        if len(type_frag_list) < 2:
            self.url_type = YouTubeUrlType.NONE
        else:
            try:
                self.url_type = YouTubeUrlType(type_frag_list[1].strip())
            except ValueError:
                self.url_type = YouTubeUrlType.NONE
                
        if self.url_type == YouTubeUrlType.CHANNEL:
            if len(type_frag_list) < 3:
                self.couldnt_find_id(url)
            else:
                self.id = type_frag_list[2]
        
        elif self.url_type == YouTubeUrlType.PLAYLIST:
            query_stuff = parse_qs(parsed.query)
            if "list" not in query_stuff:
                self.couldnt_find_id(url)
            else:
                self.id = query_stuff["list"][0]
        
        elif self.url_type == YouTubeUrlType.VIDEO:
            query_stuff = parse_qs(parsed.query)
            if "v" not in query_stuff:
                self.couldnt_find_id(url)
            else:
                self.id = query_stuff["v"][0]
            
        
    def couldnt_find_id(self, url: str):
        logging_settings["youtube_logger"].warning(f"The id is missing: {url}")
        self.url_type = YouTubeUrlType.NONE
        
    @property
    def api(self) -> str:
        if self.url_type == YouTubeUrlType.CHANNEL:
            return get_invidious_url(path=f"/api/v1/channels/playlists/{self.id}")
        
        if self.url_type == YouTubeUrlType.PLAYLIST:
            return get_invidious_url(path=f"/api/v1/playlists/{id}")
        
        if self.url_type == YouTubeUrlType.VIDEO:
            return get_invidious_url(path=f"/api/v1/videos/{self.id}")
        
        return get_invidious_url()
            
    @property
    def normal(self) -> str:
        if self.url_type.CHANNEL:
            return get_invidious_url(path=f"/channel/{self.id}")
        
        if self.url_type.PLAYLIST:
            return get_invidious_url(path="/playlist", query=f"list={self.id}")
        
        if self.url_type.VIDEO:
            return get_invidious_url(path="/watch", query=f"v={self.id}")


class SuperYouTube(Page):
    # CHANGE
    SOURCE_TYPE = ALL_SOURCE_TYPES.YOUTUBE

    NO_ADDITIONAL_DATA_FROM_SONG = False

    def __init__(self, *args, **kwargs):
        self.download_connection: Connection = Connection(
            host="https://www.youtube.com/",
            logger=self.LOGGER,
            sleep_after_404=youtube_settings["sleep_after_youtube_403"]
        )

        self.connection: Connection = Connection(
            host=get_invidious_url(),
            logger=self.LOGGER
        )
        
        # the stuff with the connection is, to ensure sponsorblock uses the proxies, my programm does
        _sponsorblock_connection: Connection = Connection()
        self.sponsorblock = python_sponsorblock.SponsorBlock(silent=True, session=_sponsorblock_connection.session)

        super().__init__(*args, **kwargs)

    def get_source_type(self, source: Source) -> Optional[Type[DatabaseObject]]:
        _url_type = {
            YouTubeUrlType.CHANNEL: Artist,
            YouTubeUrlType.PLAYLIST: Album,
            YouTubeUrlType.VIDEO: Song,
        }
        
        parsed = YouTubeUrl(source.url)
        if parsed.url_type in _url_type:
            return _url_type[parsed.url_type]

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
        r: requests.Response = self.connection.get(YouTubeUrl(source.url).api)
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

        return self.download_connection.stream_into(endpoint, target, name=desc, raw_url=True)

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
