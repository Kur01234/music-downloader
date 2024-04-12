from __future__ import unicode_literals, annotations

from typing import Dict, List, Optional, Set, Type
from urllib.parse import urlparse, urlunparse, quote, parse_qs, urlencode
import logging
import random
import json
from dataclasses import dataclass
import re
from functools import lru_cache

import youtube_dl
from youtube_dl.extractor.youtube import YoutubeIE
from youtube_dl.utils import DownloadError

from ...utils.exception.config import SettingValueError
from ...utils.config import main_settings, youtube_settings, logging_settings
from ...utils.shared import DEBUG, DEBUG_YOUTUBE_INITIALIZING
from ...utils.string_processing import clean_song_title
from ...utils import get_current_millis

from ...utils import dump_to_file

from ...objects import Source, DatabaseObject, ID3Timestamp, Artwork
from ..abstract import Page
from ...objects import (
    Artist,
    Source,
    SourcePages,
    Song,
    Album,
    Label,
    Target
)
from ...connection import Connection
from ...utils.support_classes.download_result import DownloadResult

from ._list_render import parse_renderer
from .super_youtube import SuperYouTube


def get_youtube_url(path: str = "", params: str = "", query: str = "", fragment: str = "") -> str:
    return urlunparse(("https", "music.youtube.com", path, params, query, fragment))


class YoutubeMusicConnection(Connection):
    """
    ===heartbeat=timings=for=YOUTUBEMUSIC===
    96.27
    98.16
    100.04
    101.93
    103.82

    --> average delay in between: 1.8875 min
    """

    def __init__(self, logger: logging.Logger, accept_language: str):
        # https://stackoverflow.com/questions/30561260/python-change-accept-language-using-requests
        super().__init__(
            host="https://music.youtube.com/",
            logger=logger,
            heartbeat_interval=113.25,
            header_values={
                "Accept-Language": accept_language
            },
            module="youtube_music",
        )

        # cookie consent for youtube
        # https://stackoverflow.com/a/66940841/16804841 doesn't work
        for cookie_key, cookie_value in youtube_settings["youtube_music_consent_cookies"].items():
            self.session.cookies.set(
                name=cookie_key,
                value=cookie_value,
                path='/', domain='.youtube.com'
            )

    def heartbeat(self):
        r = self.get("https://music.youtube.com/verify_session")
        if r is None:
            self.heartbeat_failed()
            return

        string = r.text

        data = json.loads(string[string.index("{"):])
        success: bool = data["success"]

        if not success:
            self.heartbeat_failed()


@dataclass
class YouTubeMusicCredentials:
    api_key: str

    # ctoken is probably short for continue-token
    # It is probably not strictly necessary, but hey :))
    ctoken: str

    # the context in requests
    context: dict

    player_url: str

    @property
    def player_id(self):
        @lru_cache(128)
        def _extract_player_info(player_url):
            _PLAYER_INFO_RE = (
                r'/s/player/(?P<id>[a-zA-Z0-9_-]{8,})/player',
                r'/(?P<id>[a-zA-Z0-9_-]{8,})/player(?:_ias\.vflset(?:/[a-zA-Z]{2,3}_[a-zA-Z]{2,3})?|-plasma-ias-(?:phone|tablet)-[a-z]{2}_[A-Z]{2}\.vflset)/base\.js$',
                r'\b(?P<id>vfl[a-zA-Z0-9_-]+)\b.*?\.js$',
            )

            for player_re in _PLAYER_INFO_RE:
                id_m = re.search(player_re, player_url)
                if id_m:
                    break
            else:
                return

            return id_m.group('id')

        return _extract_player_info(self.player_url)


class YTDLLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def debug(self, msg):
        self.logger.debug(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)


class MusicKrakenYoutubeDL(youtube_dl.YoutubeDL):
    def __init__(self, main_instance: YoutubeMusic, ydl_opts: dict, **kwargs):
        self.main_instance = main_instance
        ydl_opts = ydl_opts or {}
        ydl_opts.update({
            "logger": YTDLLogger(self.main_instance.LOGGER),
        })

        super().__init__(ydl_opts, **kwargs)
        super().__enter__()

    def __del__(self):
        super().__exit__(None, None, None)


class MusicKrakenYoutubeIE(YoutubeIE):
    def __init__(self, *args, main_instance: YoutubeMusic, **kwargs):
        self.main_instance = main_instance
        super().__init__(*args, **kwargs)




class YoutubeMusic(SuperYouTube):
    # CHANGE
    SOURCE_TYPE = SourcePages.YOUTUBE_MUSIC
    LOGGER = logging_settings["youtube_music_logger"]

    def __init__(self, *args, ydl_opts: dict = None, **kwargs):
        self.yt_music_connection: YoutubeMusicConnection = YoutubeMusicConnection(
            logger=self.LOGGER,
            accept_language="en-US,en;q=0.5"
        )
        self.credentials: YouTubeMusicCredentials = YouTubeMusicCredentials(
            api_key=youtube_settings["youtube_music_api_key"],
            ctoken="",
            context=youtube_settings["youtube_music_innertube_context"],
            player_url=youtube_settings["player_url"],
        )

        self.start_millis = get_current_millis()

        if self.credentials.api_key == "" or DEBUG_YOUTUBE_INITIALIZING:
            self._fetch_from_main_page()

        SuperYouTube.__init__(self, *args, **kwargs)

        self.download_connection: Connection = Connection(
            host="https://rr2---sn-cxaf0x-nugl.googlevideo.com/",
            logger=self.LOGGER,
            sleep_after_404=youtube_settings["sleep_after_youtube_403"],
            header_values={
                "Referer": "https://music.youtube.com/",
                'Origin': 'https://music.youtube.com',
            }
        )

        # https://github.com/ytdl-org/youtube-dl/blob/master/README.md#embedding-youtube-dl
        self.ydl = MusicKrakenYoutubeDL(self, ydl_opts)
        self.yt_ie = MusicKrakenYoutubeIE(downloader=self.ydl, main_instance=self)

        self.download_values_by_url: dict = {}
        self.not_download: Dict[str, DownloadError] = {}

    def _fetch_from_main_page(self):
        """
        ===API=KEY===
        AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30
        can be found at `view-source:https://music.youtube.com/`
        search for: "innertubeApiKey"
        """

        r = self.yt_music_connection.get("https://music.youtube.com/")
        if r is None:
            return

        if urlparse(r.url).netloc == "consent.youtube.com":
            self.LOGGER.info(f"Making cookie consent request for {type(self).__name__}.")
            r = self.yt_music_connection.post("https://consent.youtube.com/save", data={
                'gl': 'DE',
                'm': '0',
                'app': '0',
                'pc': 'ytm',
                'continue': 'https://music.youtube.com/?cbrd=1',
                'x': '6',
                'bl': 'boq_identityfrontenduiserver_20230905.04_p0',
                'hl': 'en',
                'src': '1',
                'cm': '2',
                'set_ytc': 'true',
                'set_apyt': 'true',
                'set_eom': 'false'
            })
            if r is None:
                return

            # load cookie dict from settings
            cookie_dict = youtube_settings["youtube_music_consent_cookies"]

            for cookie in r.cookies:
                cookie_dict[cookie.name] = cookie.value
            for cookie in self.yt_music_connection.session.cookies:
                cookie_dict[cookie.name] = cookie.value

            # save cookies in settings
            youtube_settings["youtube_music_consent_cookies"] = cookie_dict
        else:
            self.yt_music_connection.save(r, "index.html")

        r = self.yt_music_connection.get("https://music.youtube.com/", name="index.html")
        if r is None:
            return

        content = r.text

        if DEBUG:
            dump_to_file(f"youtube_music_index.html", r.text, exit_after_dump=False)

        # api key
        api_key_pattern = (
            r"(?<=\"innertubeApiKey\":\")(.*?)(?=\")",
            r"(?<=\"INNERTUBE_API_KEY\":\")(.*?)(?=\")",
        )

        api_keys = []
        for api_key_patter in api_key_pattern:
            api_keys.extend(re.findall(api_key_patter, content))

        found_a_good_api_key = False
        for api_key in api_keys:
            # save the first api key
            api_key = api_keys[0]

            try:
                youtube_settings["youtube_music_api_key"] = api_key
            except SettingValueError:
                continue

            found_a_good_api_key = True
            break

        if found_a_good_api_key:
            self.LOGGER.info(f"Found a valid API-KEY for {type(self).__name__}: \"{api_key}\"")
        else:
            self.LOGGER.error(f"Couldn't find an API-KEY for {type(self).__name__}. :((")

        # context
        context_pattern = r"(?<=\"INNERTUBE_CONTEXT\":{)(.*?)(?=},\"INNERTUBE_CONTEXT_CLIENT_NAME\":)"
        found_context = False
        for context_string in re.findall(context_pattern, content, re.M):
            try:
                youtube_settings["youtube_music_innertube_context"] = json.loads("{" + context_string + "}")
                found_context = True
            except json.decoder.JSONDecodeError:
                continue

            self.credentials.context = youtube_settings["youtube_music_innertube_context"]
            break

        if not found_context:
            self.LOGGER.warning(f"Couldn't find a context for {type(self).__name__}.")

        # player url
        """
        Thanks to youtube-dl <33
        """
        player_pattern = [
            r'(?<="jsUrl":")(.*?)(?=")',
            r'(?<="PLAYER_JS_URL":")(.*?)(?=")'
        ]
        found_player_url = False

        for pattern in player_pattern:
            for player_string in re.findall(pattern, content, re.M):
                try:
                    youtube_settings["player_url"] = "https://music.youtube.com" + player_string
                    found_player_url = True
                except json.decoder.JSONDecodeError:
                    continue

                self.credentials.player_url = youtube_settings["player_url"]
                break

            if found_player_url:
                break

        if not found_player_url:
            self.LOGGER.warning(f"Couldn't find an url for the video player.")

        # ytcfg
        youtube_settings["ytcfg"] = json.loads(self._search_regex(
            r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;',
            content,
            default='{}'
        )) or {}

    def get_source_type(self, source: Source) -> Optional[Type[DatabaseObject]]:
        return super().get_source_type(source)

    def general_search(self, search_query: str) -> List[DatabaseObject]:
        search_query = search_query.strip()

        urlescaped_query: str = quote(search_query.strip().replace(" ", "+"))

        # approximate the ammount of time it would take to type the search, because google for some reason tracks that
        LAST_EDITED_TIME = get_current_millis() - random.randint(0, 20)
        _estimated_time = sum(len(search_query) * random.randint(50, 100) for _ in search_query.strip())
        FIRST_EDITED_TIME = LAST_EDITED_TIME - _estimated_time if LAST_EDITED_TIME - self.start_millis > _estimated_time else random.randint(
            50, 100)

        query_continue = "" if self.credentials.ctoken == "" else f"&ctoken={self.credentials.ctoken}&continuation={self.credentials.ctoken}"

        # construct the request
        r = self.yt_music_connection.post(
            url=get_youtube_url(path="/youtubei/v1/search",
                                query=f"key={self.credentials.api_key}&prettyPrint=false" + query_continue),
            json={
                "context": {**self.credentials.context, "adSignalsInfo": {"params": []}},
                "query": search_query,
                "suggestStats": {
                    "clientName": "youtube-music",
                    "firstEditTimeMsec": FIRST_EDITED_TIME,
                    "inputMethod": "KEYBOARD",
                    "lastEditTimeMsec": LAST_EDITED_TIME,
                    "originalQuery": search_query,
                    "parameterValidationStatus": "VALID_PARAMETERS",
                    "searchMethod": "ENTER_KEY",
                    "validationStatus": "VALID",
                    "zeroPrefixEnabled": True,
                    "availableSuggestions": []
                }
            },
            headers={
                "Referer": get_youtube_url(path=f"/search", query=f"q={urlescaped_query}")
            }
        )

        if r is None:
            return []

        renderer_list = r.json().get("contents", {}).get("tabbedSearchResultsRenderer", {}).get("tabs", [{}])[0].get(
            "tabRenderer").get("content", {}).get("sectionListRenderer", {}).get("contents", [])

        if DEBUG:
            for i, content in enumerate(renderer_list):
                dump_to_file(f"{i}-renderer.json", json.dumps(content), is_json=True, exit_after_dump=False)

        results = []

        """
        cant use fixed indices, because if something has no entries, the list disappears
        instead I have to try parse everything, and just reject community playlists and profiles.
        """

        for renderer in renderer_list:
            results.extend(parse_renderer(renderer))

        return results

    def fetch_artist(self, source: Source, stop_at_level: int = 1) -> Artist:
        artist = Artist()

        # construct the request
        url = urlparse(source.url)
        browse_id = url.path.replace("/channel/", "")

        r = self.yt_music_connection.post(
            url=get_youtube_url(path="/youtubei/v1/browse", query=f"key={self.credentials.api_key}&prettyPrint=false"),
            json={
                "browseId": browse_id,
                "context": {**self.credentials.context, "adSignalsInfo": {"params": []}}
            }
        )
        if r is None:
            return artist

        if DEBUG:
            dump_to_file(f"{browse_id}.json", r.text, is_json=True, exit_after_dump=False)

        renderer_list = r.json().get("contents", {}).get("singleColumnBrowseResultsRenderer", {}).get("tabs", [{}])[
            0].get("tabRenderer", {}).get("content", {}).get("sectionListRenderer", {}).get("contents", [])

        if DEBUG:
            for i, content in enumerate(renderer_list):
                dump_to_file(f"{i}-artists-renderer.json", json.dumps(content), is_json=True, exit_after_dump=False)

        results = []

        """
        cant use fixed indices, because if something has no entries, the list dissappears
        instead I have to try parse everything, and just reject community playlists and profiles.
        """

        for renderer in renderer_list:
            results.extend(parse_renderer(renderer))

        artist.add_list_of_other_objects(results)

        return artist

    def fetch_album(self, source: Source, stop_at_level: int = 1) -> Album:
        album = Album()

        parsed_url = urlparse(source.url)
        list_id_list = parse_qs(parsed_url.query)['list']
        if len(list_id_list) <= 0:
            return album
        browse_id = list_id_list[0]

        r = self.yt_music_connection.post(
            url=get_youtube_url(path="/youtubei/v1/browse", query=f"key={self.credentials.api_key}&prettyPrint=false"),
            json={
                "browseId": browse_id,
                "context": {**self.credentials.context, "adSignalsInfo": {"params": []}}
            }
        )
        if r is None:
            return album

        if DEBUG:
            dump_to_file(f"{browse_id}.json", r.text, is_json=True, exit_after_dump=False)

        renderer_list = r.json().get("contents", {}).get("singleColumnBrowseResultsRenderer", {}).get("tabs", [{}])[
            0].get("tabRenderer", {}).get("content", {}).get("sectionListRenderer", {}).get("contents", [])

        if DEBUG:
            for i, content in enumerate(renderer_list):
                dump_to_file(f"{i}-album-renderer.json", json.dumps(content), is_json=True, exit_after_dump=False)

        results = []

        """
        cant use fixed indices, because if something has no entries, the list dissappears
        instead I have to try parse everything, and just reject community playlists and profiles.
        """

        for renderer in renderer_list:
            results.extend(parse_renderer(renderer))

        album.add_list_of_other_objects(results)

        return album


    def fetch_song(self, source: Source, stop_at_level: int = 1) -> Song:
        ydl_res: dict = {}
        try:
            ydl_res: dict = self.ydl.extract_info(url=source.url, download=False)
        except DownloadError as e:
            self.not_download[source.hash_url] = e
            self.LOGGER.error(f"Couldn't fetch song from {source.url}. {e}")
            return Song()

        self.fetch_media_url(source=source, ydl_res=ydl_res)

        artist_name = ydl_res.get("artist", ydl_res.get("uploader", "")).rstrip(" - Topic")

        album_list = []
        if "album" in ydl_res:
            album_list.append(Album(
                title=ydl_res.get("album"),
                date=ID3Timestamp.strptime(ydl_res.get("upload_date"), "%Y%m%d"),
            ))

        return Song(
            title=ydl_res.get("track", clean_song_title(ydl_res.get("title"), artist_name=artist_name)),
            note=ydl_res.get("descriptions"),
            album_list=album_list,
            length=int(ydl_res.get("duration", 0)) * 1000,
            artwork=Artwork(*ydl_res.get("thumbnails", [])),
            main_artist_list=[Artist(
                name=artist_name,
                source_list=[Source(
                    SourcePages.YOUTUBE_MUSIC, 
                    f"https://music.youtube.com/channel/{ydl_res.get('channel_id', ydl_res.get('uploader_id', ''))}"
                )]
            )],
            source_list=[Source(
                SourcePages.YOUTUBE_MUSIC,
                f"https://music.youtube.com/watch?v={ydl_res.get('id')}"
            ), source],
        )


    def fetch_media_url(self, source: Source, ydl_res: dict = None) -> dict:
        def _get_best_format(format_list: List[Dict]) -> dict:
            def _calc_score(_f: dict):
                s = 0

                _url = _f.get("url", "")
                if "mime=audio" in _url:
                    s += 100

                return s

            highest_score = 0
            best_format = {}
            for _format in format_list:
                _s = _calc_score(_format)
                if _s >= highest_score:
                    highest_score = _s
                    best_format = _format

            return best_format

        if source.url in self.download_values_by_url:
            return self.download_values_by_url[source.url]

        if ydl_res is None:
            ydl_res = self.ydl.extract_info(url=source.url, download=False)
        _best_format = _get_best_format(ydl_res.get("formats", [{}]))

        self.download_values_by_url[source.url] = {
            "url": _best_format.get("url"),
            "chunk_size": _best_format.get("downloader_options", {}).get("http_chunk_size", main_settings["chunk_size"]),
            "headers": _best_format.get("http_headers", {}),
        }

        return self.download_values_by_url[source.url]


    def download_song_to_target(self, source: Source, target: Target, desc: str = None) -> DownloadResult:
        media = self.fetch_media_url(source)

        if source.hash_url not in self.not_download:
            result = self.download_connection.stream_into(
                media["url"], 
                target, 
                name=desc, 
                raw_url=True, 
                raw_headers=True,
                disable_cache=True,
                headers=media.get("headers", {}),
                # chunk_size=media.get("chunk_size", main_settings["chunk_size"]),
                method="GET",
            )
        else:
            result = DownloadResult(error_message=str(self.not_download[source.hash_url]))

        if result.is_fatal_error:
            result.merge(super().download_song_to_target(source=source, target=target, desc=desc))

        return result


    def __del__(self):
        self.ydl.__exit__()
