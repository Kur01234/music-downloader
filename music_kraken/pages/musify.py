from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Type, Union, Generator, Dict, Any
from urllib.parse import urlparse

import pycountry
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

"""
https://musify.club/artist/ghost-bath-280348?_pjax=#bodyContent
https://musify.club/artist/ghost-bath-280348/releases?_pjax=#bodyContent
https://musify.club/artist/ghost-bath-280348/clips?_pjax=#bodyContent
https://musify.club/artist/ghost-bath-280348/photos?_pjax=#bodyContent

POST https://musify.club/artist/filtersongs
ID: 280348
NameForUrl: ghost-bath
Page: 1
IsAllowed: True
SortOrder.Property: dateCreated
SortOrder.IsAscending: false
X-Requested-With: XMLHttpRequest

POST https://musify.club/artist/filteralbums
ArtistID: 280348
SortOrder.Property: dateCreated
SortOrder.IsAscending: false
X-Requested-With: XMLHttpRequest
"""


class MusifyTypes(Enum):
    ARTIST = "artist"
    RELEASE = "release"
    SONG = "track"


@dataclass
class MusifyUrl:
    source_type: MusifyTypes
    name_without_id: str
    name_with_id: str
    musify_id: str
    url: str
    

ALBUM_TYPE_MAP = defaultdict(lambda: AlbumType.OTHER, {
    1: AlbumType.OTHER,                 # literally other xD
    2: AlbumType.STUDIO_ALBUM,
    3: AlbumType.EP,
    4: AlbumType.SINGLE,
    5: AlbumType.OTHER,                 # BOOTLEG
    6: AlbumType.LIVE_ALBUM,
    7: AlbumType.COMPILATION_ALBUM,     # compilation of different artists
    8: AlbumType.MIXTAPE,
    9: AlbumType.DEMO,
    10: AlbumType.MIXTAPE,              # DJ Mixes
    11: AlbumType.COMPILATION_ALBUM,    # compilation of only this artist
    12: AlbumType.STUDIO_ALBUM,         # split
    13: AlbumType.COMPILATION_ALBUM,    # unofficial
    14: AlbumType.MIXTAPE               # "Soundtracks"
})

    
def parse_url(url: str) -> MusifyUrl:
    parsed = urlparse(url)

    path = parsed.path.split("/")

    split_name = path[2].split("-")
    url_id = split_name[-1]
    name_for_url = "-".join(split_name[:-1])

    try:
        type_enum = MusifyTypes(path[1])
    except ValueError as e:
        logging_settings["musify_logger"].warning(f"{path[1]} is not yet implemented, add it to MusifyTypes")
        raise e

    return MusifyUrl(
        source_type=type_enum,
        name_without_id=name_for_url,
        name_with_id=path[2],
        musify_id=url_id,
        url=url
    )


class Musify(Page):
    SOURCE_TYPE = ALL_SOURCE_TYPES.MUSIFY
    
    HOST = "https://musify.club"
    
    def __init__(self, *args, **kwargs):
        self.connection: Connection = Connection(
            host="https://musify.club/",
            logger=self.LOGGER,
            module="musify",
        )

        self.stream_connection: Connection = Connection(
            host="https://musify.club/",
            logger=self.LOGGER,
            semantic_not_found=False,
        )
        
        super().__init__(*args, **kwargs)

    def get_source_type(self, source: Source) -> Optional[Type[DatabaseObject]]:
        if source.url is None:
            return None
        
        musify_url = parse_url(source.url)
        
        # Has no labels, because afaik musify has no Labels
        musify_type_to_database_type = {
            MusifyTypes.SONG: Song,
            MusifyTypes.RELEASE: Album,
            MusifyTypes.ARTIST: Artist
        }
        
        return musify_type_to_database_type.get(musify_url.source_type)
    
    def _parse_artist_contact(self, contact: BeautifulSoup) -> Artist:
        source_list: List[Source] = []
        name = None
        _id = None

        # source
        anchor = contact.find("a")
        if anchor is not None:
            href = anchor.get("href")
            name = anchor.get("title")

            if "-" in href:
                _id = href.split("-")[-1]

            source_list.append(Source(self.SOURCE_TYPE, self.HOST + href))

        # artist image
        image_soup = contact.find("img")
        if image_soup is not None:
            alt = image_soup.get("alt")
            if alt is not None:
                name = alt

            artist_thumbnail = image_soup.get("src")

        return Artist(
            name=name,
            source_list=source_list
        )
        
    def _parse_album_contact(self, contact: BeautifulSoup) -> Album:
        """
        <div class="contacts__item">
            <a href="/release/ghost-bath-ghost-bath-2013-602489" title="Ghost Bath - 2013">
            
            <div class="contacts__img release">
                <img alt="Ghost Bath" class="lozad" data-src="https://37s.musify.club/img/69/9060265/24178833.jpg"/>
                <noscript><img alt="Ghost Bath" src="https://37s.musify.club/img/69/9060265/24178833.jpg"/></noscript>
            </div>
            
            <div class="contacts__info">
                <strong>Ghost Bath - 2013</strong>
                <small>Ghost Bath</small>
                <small>Треков: 4</small>    <!--tracks-->
                <small><i class="zmdi zmdi-star zmdi-hc-fw"></i> 9,04</small>
            </div>
            </a>
        </div>
        """

        source_list: List[Source] = []
        title = None
        _id = None
        year = None
        artist_list: List[Artist] = []

        def parse_title_date(title_date: Optional[str], delimiter: str = " - "):
            nonlocal year
            nonlocal title

            if title_date is None:
                return

            title_date = title_date.strip()
            split_attr = title_date.split(delimiter)

            if len(split_attr) < 2:
                return
            if not split_attr[-1].isdigit():
                return

            year = int(split_attr[-1])
            title = delimiter.join(split_attr[:-1])

        # source
        anchor = contact.find("a")
        if anchor is not None:
            href = anchor.get("href")

            # get the title and year
            parse_title_date(anchor.get("title"))

            if "-" in href:
                _id = href.split("-")[-1]

            source_list.append(Source(self.SOURCE_TYPE, self.HOST + href))

        # cover art
        image_soup = contact.find("img")
        if image_soup is not None:
            alt = image_soup.get("alt")
            if alt is not None:
                title = alt

            cover_art = image_soup.get("src")

        contact_info_soup = contact.find("div", {"class": "contacts__info"})
        if contact_info_soup is not None:
            """
            <strong>Ghost Bath - 2013</strong>
            <small>Ghost Bath</small>
            <small>Треков: 4</small>    <!--tracks-->
            <small><i class="zmdi zmdi-star zmdi-hc-fw"></i> 9,04</small>
            """

            title_soup = contact_info_soup.find("strong")
            if title_soup is None:
                parse_title_date(title_soup)

            small_list = contact_info_soup.find_all("small")
            if len(small_list) == 3:
                # artist
                artist_soup: BeautifulSoup = small_list[0]
                raw_artist_str = artist_soup.text

                for artist_str in raw_artist_str.split("&\r\n"):
                    artist_str = artist_str.rstrip("& ...\r\n")
                    artist_str = artist_str.strip()

                    if artist_str.endswith("]") and "[" in artist_str:
                        artist_str = artist_str.rsplit("[", maxsplit=1)[0]

                    artist_list.append(Artist(name=artist_str))

                track_count_soup: BeautifulSoup = small_list[1]
                rating_soup: BeautifulSoup = small_list[2]
            else:
                self.LOGGER.warning("got an unequal ammount than 3 small elements")

        return Album(
            title=title,
            source_list=source_list,
            date=ID3Timestamp(year=year),
            artist_list=artist_list
        )
    
    def _parse_contact_container(self, contact_container_soup: BeautifulSoup) -> List[Union[Artist, Album]]:
        contacts = []

        contact: BeautifulSoup
        for contact in contact_container_soup.find_all("div", {"class": "contacts__item"}):

            anchor_soup = contact.find("a")

            if anchor_soup is not None:
                url = anchor_soup.get("href")

                if url is not None:
                    if "artist" in url:
                        contacts.append(self._parse_artist_contact(contact))
                    elif "release" in url:
                        contacts.append(self._parse_album_contact(contact))
        return contacts

    def _parse_playlist_item(self, playlist_item_soup: BeautifulSoup) -> Song:
        _id = None
        song_title = playlist_item_soup.get("data-name")
        artist_list: List[Artist] = []
        source_list: List[Source] = []

        # details
        playlist_details: BeautifulSoup = playlist_item_soup.find("div", {"class", "playlist__heading"})
        if playlist_details is not None:
            anchor_list = playlist_details.find_all("a")

            if len(anchor_list) >= 2:
                # artists
                artist_anchor: BeautifulSoup
                for artist_anchor in anchor_list[:-1]:
                    _id = None
                    href = artist_anchor.get("href")
                    artist_source: Source = Source(self.SOURCE_TYPE, self.HOST + href)
                    if "-" in href:
                        _id = href.split("-")[-1]

                    artist_list.append(Artist(
                        name=artist_anchor.get_text(strip=True),
                        source_list=[artist_source]
                    ))

                # track
                track_soup: BeautifulSoup = anchor_list[-1]
                """
                TODO
                this anchor text may have something like (feat. some artist)
                which is not acceptable
                """
                href = track_soup.get("href")
                if href is not None:
                    if "-" in href:
                        raw_id: str = href.split("-")[-1]
                        if raw_id.isdigit():
                            _id = raw_id
                    source_list.append(Source(self.SOURCE_TYPE, self.HOST + href))

            else:
                self.LOGGER.debug("there are not enough anchors (2) for artist and track")
                self.LOGGER.debug(str(artist_list))

        """
        artist_name = playlist_item_soup.get("data-artist")
        if artist_name is not None:
            artist_list.append(Artist(name=artist_name))
        """
        id_attribute = playlist_item_soup.get("id")
        if id_attribute is not None:
            raw_id = id_attribute.replace("playerDiv", "")
            if raw_id.isdigit():
                _id = raw_id



        return Song(
            title=clean_song_title(song_title, artist_name=artist_list[0].name if len(artist_list) > 0 else None),
            feature_artist_list=artist_list,
            source_list=source_list
        )

    def _parse_playlist_soup(self, playlist_soup: BeautifulSoup) -> List[Song]:
        song_list = []

        for playlist_item_soup in playlist_soup.find_all("div", {"class": "playlist__item"}):
            song_list.append(self._parse_playlist_item(playlist_item_soup))

        return song_list
        
    def general_search(self, search_query: str) -> List[DatabaseObject]:
        search_results = []

        r = self.connection.get(f"https://musify.club/search?searchText={search_query}", name="search_" + search_query)
        if r is None:
            return []
        search_soup: BeautifulSoup = self.get_soup_from_response(r)

        # album and songs
        # child of div class: contacts row
        for contact_container_soup in search_soup.find_all("div", {"class": "contacts"}):
            search_results.extend(self._parse_contact_container(contact_container_soup))

        # song
        # div class: playlist__item
        for playlist_soup in search_soup.find_all("div", {"class": "playlist"}):
            search_results.extend(self._parse_playlist_soup(playlist_soup))

        return search_results
    
    def fetch_song(self, source: Source, stop_at_level: int = 1) -> Song:
        musify_url = parse_url(source.url)

        r = self.connection.get(source.url, name="track_" + musify_url.name_with_id)
        if r is None:
            return Song()
        
        soup = self.get_soup_from_response(r)
        
        track_name: str = None
        source_list: List[Source] = [source]
        lyrics_list: List[Lyrics] = []
        artist_list: List[Artist] = []
        album_list: List[Album] = []
        
        def _parse_artist_anchor(artist_soup: BeautifulSoup):
            nonlocal artist_list
            if artist_soup is None:
                return
            
            artist_src_list = []
            artist_name = None
            
            href = artist_soup["href"]
            if href is not None:
                href_parts = href.split("/")
                if len(href_parts) <= 1 or href_parts[-2] != "artist":
                    return

                artist_src_list.append(Source(self.SOURCE_TYPE, self.HOST + href))

            name_elem: BeautifulSoup = artist_soup.find("span", {"itemprop": "name"})
            if name_elem is not None:
                artist_name = name_elem.text.strip()
                
            artist_list.append(Artist(name=artist_name, source_list=artist_src_list))    
    
        def _parse_album_anchor(album_soup: BeautifulSoup):
            nonlocal album_list
            if album_anchor is None:
                return
            album_source_list = []
            album_name = None
            
            href = album_soup["href"]
            if href is not None:
                album_source_list.append(Source(self.SOURCE_TYPE, self.HOST + href))

            name_elem: BeautifulSoup = album_soup.find("span", {"itemprop": "name"})
            if name_elem is not None:
                album_name = name_elem.text.strip()
                
            album_list.append(Album(title=album_name, source_list=album_source_list))

        # download url
        anchor: BeautifulSoup
        for anchor in soup.find_all("a", {"itemprop": "audio"}):
            href = anchor["href"]
            if href is not None:
                source.audio_url = self.HOST + href
    
        # song detail
        album_info: BeautifulSoup
        for album_info in soup.find_all("ul", {"class": "album-info"}):
            list_element: BeautifulSoup = album_info.find("li")
            
            if list_element is not None:
                artist_soup: BeautifulSoup
                for artist_soup in list_element.find_all("a"):
                    artist_source_list = []
                    href = artist_soup["href"]
                    if href is not None:
                        artist_source_list = [Source(self.SOURCE_TYPE, self.HOST + href)]
                    artist_list.append(Artist(
                        name=artist_soup.text.strip(),
                        source_list=artist_source_list
                    ))
    
        # breadcrums
        breadcrumb_list_element_list: List[BeautifulSoup] = soup.find_all("ol", {"class": "breadcrumb"})
        for breadcrumb_list_element in breadcrumb_list_element_list:
            list_points: List[BeautifulSoup] = breadcrumb_list_element.find_all("li", "breadcrumb-item")
            if len(list_points) != 5:
                self.LOGGER.warning(f"breadcrumbs of song doesn't have 5 items: {breadcrumb_list_element.prettify()}")
                break
            
            artist_anchor: BeautifulSoup = list_points[2].find("a")
            _parse_artist_anchor(artist_anchor)
            
            album_anchor: BeautifulSoup = list_points[3].find("a")
            _parse_album_anchor(album_anchor)
            
            track_name = list_points[4].text.strip()

        # artwork
        artwork: Artwork = Artwork()
        album_image_element_list: List[BeautifulSoup] = soup.find_all("img", {"class": "album-img"})
        for album_image_element in album_image_element_list:
            artwork.append(url=album_image_element.get("data-src", album_image_element.get("src")))
        
        # lyrics
        lyrics_container: List[BeautifulSoup] = soup.find_all("div", {"id": "tabLyrics"})
        for lyrics in lyrics_container:
            lyrics_text = lyrics.find("div", {"style": "white-space: pre-line"}).text.strip()
            lyrics_list.append(Lyrics(text=FormattedText(html=lyrics_text)))
        
        # youtube video
        video_container_list: List[BeautifulSoup] = soup.find_all("div", {"id": "tabVideo"})
        for video_container in video_container_list:
            iframe_list: List[BeautifulSoup] = video_container.findAll("iframe")
            for iframe in iframe_list:
                """
                the url could look like this
                https://www.youtube.com/embed/sNObCkhzOYA?si=dNVgnZMBNVlNb0P_
                """
                parsed_url = urlparse(iframe["src"])
                path_parts = parsed_url.path.strip("/").split("/")
                if path_parts[0] != "embed" or len(path_parts) < 2:
                    continue
                
                source_list.append(Source(
                    ALL_SOURCE_TYPES.YOUTUBE,
                    f"https://music.youtube.com/watch?v={path_parts[1]}",
                    referrer_page=self.SOURCE_TYPE
                ))
        
        return Song(
            title=clean_song_title(track_name, artist_name=artist_list[0].name if len(artist_list) > 0 else None),
            source_list=source_list,
            lyrics_list=lyrics_list,
            feature_artist_list=artist_list,
            album_list=album_list,
            artwork=artwork,
        )

    def _parse_song_card(self, song_card: BeautifulSoup) -> Song:
        """
            <div id="playerDiv3051" class="playlist__item" itemprop="track" itemscope="itemscope" itemtype="http://schema.org/MusicRecording" data-artist="Linkin Park" data-name="Papercut">
                <div id="play_3051" class="playlist__control play" data-url="/track/play/3051/linkin-park-papercut.mp3" data-position="1" data-title="Linkin Park - Papercut" title="Слушать Linkin Park - Papercut">
                    <span class="ico-play"><i class="zmdi zmdi-play-circle-outline zmdi-hc-2-5x"></i></span>
                    <span class="ico-pause"><i class="zmdi zmdi-pause-circle-outline zmdi-hc-2-5x"></i></span>
                </div>
                <div class="playlist__position">
                    1
                </div>
                <div class="playlist__details">
                    <div class="playlist__heading">
                        <a href="/artist/linkin-park-5" rel="nofollow">Linkin Park</a> - <a class="strong" href="/track/linkin-park-papercut-3051">Papercut</a>
                        <span itemprop="byArtist" itemscope="itemscope" itemtype="http://schema.org/MusicGroup">
                            <meta content="/artist/linkin-park-5" itemprop="url" />
                            <meta content="Linkin Park" itemprop="name" />
                        </span>
                    </div>
                </div>
                <div>
                    <div class="track__details track__rating hidden-xs-down">
                        <span class="text-muted">
                            <i class="zmdi zmdi-star-circle zmdi-hc-1-3x" title="Рейтинг"></i>
                            326,3K
                        </span>
                    </div>
                </div>
                <div class="track__details hidden-xs-down">
                    <span class="text-muted">03:05</span>
                    <span class="text-muted">320 Кб/с</span>
                </div>
                <div class="track__details hidden-xs-down">
                    <span title='Есть видео Linkin Park - Papercut'><i class='zmdi zmdi-videocam zmdi-hc-1-3x'></i></span>
                    <span title='Есть текст Linkin Park - Papercut'><i class='zmdi zmdi-file-text zmdi-hc-1-3x'></i></span>
                </div>
                <div class="playlist__actions">
                    <span class="pl-btn save-to-pl" id="add_3051" title="Сохранить в плейлист"><i class="zmdi zmdi-plus zmdi-hc-1-5x"></i></span>
                    <a target="_blank" itemprop="audio" download="Linkin Park - Papercut.mp3" href="/track/dl/3051/linkin-park-papercut.mp3" class="no-ajaxy yaBrowser" id="dl_3051" title='Скачать Linkin Park - Papercut'>
                        <span><i class="zmdi zmdi-download zmdi-hc-2-5x"></i></span>
                    </a>
                </div>
            </div>
        """
        song_name = song_card.get("data-name")
        artist_list: List[Artist] = []
        source_list: List[Source] = []
        tracksort = None

        current_url = None

        def parse_title(_title: str) -> str:
            return _title

        """
        # get from parent div
        _artist_name = song_card.get("data-artist")
        if _artist_name is not None:
            artist_list.append(Artist(name=_artist_name))
        """

        # get tracksort
        tracksort_soup: BeautifulSoup = song_card.find("div", {"class": "playlist__position"})
        if tracksort_soup is not None:
            raw_tracksort: str = tracksort_soup.get_text(strip=True)
            if raw_tracksort.isdigit():
                tracksort = int(raw_tracksort)

        # playlist details
        playlist_details: BeautifulSoup = song_card.find("div", {"class": "playlist__details"})
        if playlist_details is not None:
            """
            <div class="playlist__heading">
                <a href="/artist/tamas-141317" rel="nofollow">Tamas</a> ft.<a href="/artist/zombiez-630767" rel="nofollow">Zombiez</a> - <a class="strong" href="/track/tamas-zombiez-voodoo-feat-zombiez-16185276">Voodoo (Feat. Zombiez)</a>                            
                <span itemprop="byArtist" itemscope="itemscope" itemtype="http://schema.org/MusicGroup">
                    <meta content="/artist/tamas-141317" itemprop="url" />
                    <meta content="Tamas" itemprop="name" />
                </span>
                <span itemprop="byArtist" itemscope="itemscope" itemtype="http://schema.org/MusicGroup">
                    <meta content="/artist/zombiez-630767" itemprop="url" />
                    <meta content="Zombiez" itemprop="name" />
                </span>
            </div>
            """
            # track
            anchor_list: List[BeautifulSoup] = playlist_details.find_all("a")
            if len(anchor_list) > 1:
                track_anchor: BeautifulSoup = anchor_list[-1]
                href: str = track_anchor.get("href")
                if href is not None:
                    current_url = self.HOST + href
                    source_list.append(Source(self.SOURCE_TYPE, self.HOST + href))
                song_name = parse_title(track_anchor.get_text(strip=True))

            # artist
            artist_span: BeautifulSoup
            for artist_span in playlist_details.find_all("span", {"itemprop": "byArtist"}):
                _artist_src = None
                _artist_name = None
                meta_artist_src = artist_span.find("meta", {"itemprop": "url"})
                if meta_artist_src is not None:
                    meta_artist_url = meta_artist_src.get("content")
                    if meta_artist_url is not None:
                        _artist_src = [Source(self.SOURCE_TYPE, self.HOST + meta_artist_url)]

                meta_artist_name = artist_span.find("meta", {"itemprop": "name"})
                if meta_artist_name is not None:
                    meta_artist_name_text = meta_artist_name.get("content")
                    _artist_name = meta_artist_name_text

                if _artist_name is not None or _artist_src is not None:
                    artist_list.append(Artist(name=_artist_name, source_list=_artist_src))

        # playlist actions
        playlist_actions: BeautifulSoup = song_card.find("div", {"class": "playlist__actions"})
        if playlist_actions is not None:
            """
            <div class="playlist__actions">
                <span class="pl-btn save-to-pl" id="add_3051" title="Сохранить в плейлист"><i class="zmdi zmdi-plus zmdi-hc-1-5x"></i></span>
                <a target="_blank" itemprop="audio" download="Linkin Park - Papercut.mp3" href="/track/dl/3051/linkin-park-papercut.mp3" class="no-ajaxy yaBrowser" id="dl_3051" title='Скачать Linkin Park - Papercut'>
                    <span><i class="zmdi zmdi-download zmdi-hc-2-5x"></i></span>
                </a>
            </div>
            """
            # getting the actual download link:
            download_anchor = playlist_actions.find("a", {"itemprop": "audio"})
            if download_anchor is not None:
                download_href = download_anchor.get("href")
                if download_href is not None and current_url is not None:
                    source_list.append(Source(
                        self.SOURCE_TYPE,
                        url=current_url,
                        audio_url=self.HOST + download_href
                    ))

        return Song(
            title=clean_song_title(song_name, artist_name=artist_list[0].name if len(artist_list) > 0 else None),
            tracksort=tracksort,
            feature_artist_list=artist_list,
            source_list=source_list
        )

    
    def _parse_album(self, soup: BeautifulSoup) -> Album:
        name: str = None
        source_list: List[Source] = []
        artist_list: List[Artist] = []
        date: ID3Timestamp = None

        """
        if breadcrumb list has 4 elements, then
        the -2 is the artist link,
        the -1 is the album
        """
        # breadcrumb
        breadcrumb_soup: BeautifulSoup = soup.find("ol", {"class", "breadcrumb"})
        breadcrumb_elements: List[BeautifulSoup] = breadcrumb_soup.find_all("li", {"class": "breadcrumb-item"})
        if len(breadcrumb_elements) == 4:
            # album
            album_crumb: BeautifulSoup = breadcrumb_elements[-1]
            name = album_crumb.text.strip()

            # artist
            artist_crumb: BeautifulSoup = breadcrumb_elements[-2]
            anchor: BeautifulSoup = artist_crumb.find("a")
            if anchor is not None:
                href = anchor.get("href")

                href_parts = href.split("/")
                if not(len(href_parts) <= 1 or href_parts[-2] != "artist"):
                    artist_source_list: List[Source] = []

                    if href is not None:
                        artist_source_list.append(Source(self.SOURCE_TYPE, self.HOST + href.strip()))

                    span: BeautifulSoup = anchor.find("span")
                    if span is not None:
                        artist_list.append(Artist(
                            name=span.get_text(strip=True),
                            source_list=artist_source_list
                        ))
        else:
            self.LOGGER.debug("there are not 4 breadcrumb items, which shouldn't be the case")

        # meta
        meta_url: BeautifulSoup = soup.find("meta", {"itemprop": "url"})
        if meta_url is not None:
            url = meta_url.get("content")
            if url is not None:
                source_list.append(Source(self.SOURCE_TYPE, self.HOST + url))

        meta_name: BeautifulSoup = soup.find("meta", {"itemprop": "name"})
        if meta_name is not None:
            _name = meta_name.get("content")
            if _name is not None:
                name = _name
                
        # album info
        album_info_ul: BeautifulSoup = soup.find("ul", {"class": "album-info"})
        if album_info_ul is not None:
            artist_anchor: BeautifulSoup
            for artist_anchor in album_info_ul.find_all("a", {"itemprop": "byArtist"}):
                # line 98
                artist_source_list: List[Source] = []

                artist_url_meta = artist_anchor.find("meta", {"itemprop": "url"})
                if artist_url_meta is not None:
                    artist_href = artist_url_meta.get("content")
                    if artist_href is not None:
                        artist_source_list.append(Source(self.SOURCE_TYPE, url=self.HOST + artist_href))

                artist_meta_name = artist_anchor.find("meta", {"itemprop": "name"})
                if artist_meta_name is not None:
                    artist_name = artist_meta_name.get("content")
                    if artist_name is not None:
                        artist_list.append(Artist(
                            name=artist_name,
                            source_list=artist_source_list
                        ))

            time_soup: BeautifulSoup = album_info_ul.find("time", {"itemprop": "datePublished"})
            if time_soup is not None:
                raw_datetime = time_soup.get("datetime")
                if raw_datetime is not None:
                    try:
                        date = ID3Timestamp.strptime(raw_datetime, "%Y-%m-%d")
                    except ValueError:
                        self.LOGGER.debug(f"Raw datetime doesn't match time format %Y-%m-%d: {raw_datetime}")

        return Album(
            title=name,
            source_list=source_list,
            artist_list=artist_list,
            date=date
        )

    def fetch_album(self, source: Source, stop_at_level: int = 1) -> Album:
        """
        fetches album from source:
        eg. 'https://musify.club/release/linkin-park-hybrid-theory-2000-188'

        /html/musify/album_overview.html
        - [x] tracklist
        - [x] attributes
        - [ ] ratings

        :param stop_at_level:
        :param source:
        :return:
        """

        url = parse_url(source.url)

        endpoint = self.HOST + "/release/" + url.name_with_id
        r = self.connection.get(endpoint, name=url.name_with_id)
        if r is None:
            return Album()

        soup = BeautifulSoup(r.content, "html.parser")

        album = self._parse_album(soup)

        # <div class="card"><div class="card-body">...</div></div>
        cards_soup: BeautifulSoup = soup.find("div", {"class": "card-body"})
        if cards_soup is not None:
            card_soup: BeautifulSoup
            for card_soup in cards_soup.find_all("div", {"class": "playlist__item"}):
                new_song = self._parse_song_card(card_soup)
                album.song_collection.append(new_song)
        
        album.update_tracksort()

        return album
    
    def _fetch_initial_artist(self, url: MusifyUrl, source: Source, **kwargs) -> Artist:
        """
        https://musify.club/artist/ghost-bath-280348?_pjax=#bodyContent
        """

        r = self.connection.get(f"https://musify.club/{url.source_type.value}/{url.name_with_id}?_pjax=#bodyContent", name="artist_attributes_" + url.name_with_id)
        if r is None:
            return Artist(source_list=[source])

        soup = self.get_soup_from_response(r)

        """
        <ol class="breadcrumb" itemscope="" itemtype="http://schema.org/BreadcrumbList">
            <li class="breadcrumb-item" itemprop="itemListElement" itemscope="" itemtype="http://schema.org/ListItem"><a href="/" itemprop="item"><span itemprop="name">Главная</span><meta content="1" itemprop="position"/></a></li>
            <li class="breadcrumb-item" itemprop="itemListElement" itemscope="" itemtype="http://schema.org/ListItem"><a href="/artist" itemprop="item"><span itemprop="name">Исполнители</span><meta content="2" itemprop="position"/></a></li>
            <li class="breadcrumb-item active">Ghost Bath</li>
        </ol>
        
        <ul class="nav nav-tabs nav-fill">
            <li class="nav-item"><a class="active nav-link" href="/artist/ghost-bath-280348">песни (41)</a></li>
            <li class="nav-item"><a class="nav-link" href="/artist/ghost-bath-280348/releases">альбомы (12)</a></li>
            <li class="nav-item"><a class="nav-link" href="/artist/ghost-bath-280348/clips">видеоклипы (23)</a></li>
            <li class="nav-item"><a class="nav-link" href="/artist/ghost-bath-280348/photos">фото (38)</a></li>
        </ul>
        
        <header class="content__title">
            <h1>Ghost Bath</h1>
            <div class="actions">
                ...
            </div>
        </header>
        
        <ul class="icon-list">
            <li>
                <i class="zmdi zmdi-globe zmdi-hc-fw" title="Страна"></i> 
                <i class="flag-icon US shadow"></i>
                Соединенные Штаты
            </li>
        </ul>
        """
        name = None
        source_list: List[Source] = []
        country = None
        notes: FormattedText = FormattedText()

        breadcrumbs: BeautifulSoup = soup.find("ol", {"class": "breadcrumb"})
        if breadcrumbs is not None:
            breadcrumb_list: List[BeautifulSoup] = breadcrumbs.find_all("li", {"class": "breadcrumb-item"}, recursive=False)
            if len(breadcrumb_list) == 3:
                name = breadcrumb_list[-1].get_text(strip=True)
            else:
                self.LOGGER.debug("breadcrumb layout on artist page changed")

        nav_tabs: BeautifulSoup = soup.find("ul", {"class": "nav-tabs"})
        if nav_tabs is not None:
            list_item: BeautifulSoup
            for list_item in nav_tabs.find_all("li", {"class": "nav-item"}, recursive=False):
                if not list_item.get_text(strip=True).startswith("песни"):
                    # "песни" translates to "songs"
                    continue

                anchor: BeautifulSoup = list_item.find("a")
                if anchor is None:
                    continue
                href = anchor.get("href")
                if href is None:
                    continue

                source_list.append(Source(
                    self.SOURCE_TYPE,
                    self.HOST + href
                ))

        content_title: BeautifulSoup = soup.find("header", {"class": "content__title"})
        if content_title is not None:
            h1_name: BeautifulSoup = content_title.find("h1", recursive=False)
            if h1_name is not None:
                name = h1_name.get_text(strip=True)

        # country and sources
        icon_list: BeautifulSoup = soup.find("ul", {"class": "icon-list"})
        if icon_list is not None:
            country_italic: BeautifulSoup = icon_list.find("i", {"class", "flag-icon"})
            if country_italic is not None:
                style_classes: set = {'flag-icon', 'shadow'}
                classes: set = set(country_italic.get("class"))

                country_set: set = classes.difference(style_classes)
                if len(country_set) != 1:
                    self.LOGGER.debug("the country set contains multiple values")
                if len(country_set) != 0:
                    """
                    This is the css file, where all flags that can be used on musify
                    are laid out and styled.
                    Every flag has two upper case letters, thus I assume they follow the alpha_2
                    https://musify.club/content/flags.min.css
                    """

                    country = pycountry.countries.get(alpha_2=list(country_set)[0])

            # get all additional sources
            additional_source: BeautifulSoup
            for additional_source in icon_list.find_all("a", {"class", "link"}):
                href = additional_source.get("href")
                if href is None:
                    continue
                new_src = Source.match_url(href, referrer_page=self.SOURCE_TYPE)
                if new_src is None:
                    continue
                source_list.append(new_src)

        note_soup: BeautifulSoup = soup.find(id="text-main")
        if note_soup is not None:
            notes.html = note_soup.decode_contents()

        return Artist(
            name=name,
            country=country,
            source_list=source_list,
            notes=notes
        )

    def _parse_album_card(self, album_card: BeautifulSoup, artist_name: str = None, **kwargs) -> Album:
        """
        <div class="card release-thumbnail" data-type="2">
            <a href="/release/ghost-bath-self-loather-2021-1554266">
                <img alt="Self Loather" class="card-img-top lozad" data-src="https://40s-a.musify.club/img/70/24826582/62624396.jpg"/>
                <noscript><img alt="Self Loather" src="https://40s-a.musify.club/img/70/24826582/62624396.jpg"/></noscript>
            </a>
            <div class="card-body">
                <h4 class="card-subtitle">
                <a href="/release/ghost-bath-self-loather-2021-1554266">Self Loather</a>
                </h4>
            </div>
            <div class="card-footer"><p class="card-text"><a href="/albums/2021">2021</a></p></div>
            <div class="card-footer">
                <p class="card-text genre__labels">
                <a href="/genre/depressive-black-132">Depressive Black</a><a href="/genre/post-black-metal-295">Post-Black Metal</a> </p>
            </div>
            <div class="card-footer">
                <small><i class="zmdi zmdi-calendar" title="Добавлено"></i> 13.11.2021</small>
                <small><i class="zmdi zmdi-star zmdi-hc-fw" title="Рейтинг"></i> 5,88</small>
            </div>
        </div>
        """

        album_kwargs: Dict[str, Any] = {
            "source_list": [],
        }

        album_status_id = album_card.get("data-type")
        if album_status_id.isdigit():
            album_status_id = int(album_status_id)
        album_kwargs["album_type"] = ALBUM_TYPE_MAP[album_status_id]

        if album_status_id == 5:
            album_kwargs["album_status"] = AlbumStatus.BOOTLEG

        def parse_release_anchor(_anchor: BeautifulSoup, text_is_name=False):
            nonlocal album_kwargs

            if _anchor is None:
                return

            href = _anchor.get("href")
            if href is not None:
                # add url to sources
                album_kwargs["source_list"].append(Source(
                    self.SOURCE_TYPE,
                    self.HOST + href
                ))

            if text_is_name:
                album_kwargs["title"] = clean_song_title(_anchor.text, artist_name)

        anchor_list = album_card.find_all("a", recursive=False)
        if len(anchor_list) > 0:
            anchor = anchor_list[0]
            parse_release_anchor(anchor)

            thumbnail: BeautifulSoup = anchor.find("img")
            if thumbnail is not None:
                alt = thumbnail.get("alt")
                if alt is not None:
                    album_kwargs["title"] = clean_song_title(alt, artist_name)

                image_url = thumbnail.get("src")
        else:
            self.LOGGER.debug("the card has no thumbnail or url")

        card_body = album_card.find("div", {"class": "card-body"})
        if card_body is not None:
            parse_release_anchor(card_body.find("a"), text_is_name=True)

        def parse_small_date(small_soup: BeautifulSoup):
            """
            <small>
                <i class="zmdi zmdi-calendar" title="Добавлено"></i>
                13.11.2021
            </small>
            """
            nonlocal album_kwargs

            italic_tagging_soup: BeautifulSoup = small_soup.find("i")
            if italic_tagging_soup is None:
                return
            if italic_tagging_soup.get("title") != "Добавлено":
                # "Добавлено" can be translated to "Added (at)"
                return

            raw_time = small_soup.text.strip()
            album_kwargs["date"] = ID3Timestamp.strptime(raw_time, "%d.%m.%Y")

        # parse small date
        card_footer_list = album_card.find_all("div", {"class": "card-footer"})
        if len(card_footer_list) != 3:
            self.LOGGER.debug("there are not exactly 3 card footers in a card")

        if len(card_footer_list) > 0:
            for any_small_soup in card_footer_list[-1].find_all("small"):
                parse_small_date(any_small_soup)
        else:
            self.LOGGER.debug("there is not even 1 footer in the album card")

        return Album(**album_kwargs)

    def _fetch_artist_discography(self, artist: Artist, url: MusifyUrl, artist_name: str = None, **kwargs):
        """
        POST https://musify.club/artist/filteralbums
            ArtistID: 280348
            SortOrder.Property: dateCreated
            SortOrder.IsAscending: false
            X-Requested-With: XMLHttpRequest
        """
        _download_all = kwargs.get("download_all", False)
        _album_type_blacklist = kwargs.get("album_type_blacklist", main_settings["album_type_blacklist"])

        endpoint = self.HOST + "/" + url.source_type.value + "/filteralbums"

        r = self.connection.post(url=endpoint, json={
            "ArtistID": str(url.musify_id),
            "SortOrder.Property": "dateCreated",
            "SortOrder.IsAscending": False,
            "X-Requested-With": "XMLHttpRequest"
        }, name="discography_" + url.name_with_id)
        if r is None:
            return

        soup: BeautifulSoup = self.get_soup_from_response(r)

        for card_soup in soup.find_all("div", {"class": "card"}):
            album = self._parse_album_card(card_soup, artist_name, **kwargs)
            if not self.fetch_options.download_all and album.album_type in self.fetch_options.album_type_blacklist:
                continue

            artist.album_collection.append(album)

    def fetch_artist(self, source: Source, **kwargs) -> Artist:
        """
        TODO
        [x] discography
        [x] attributes
        [] picture gallery
        """

        url = parse_url(source.url)

        artist = self._fetch_initial_artist(url, source=source, **kwargs)
        self._fetch_artist_discography(artist, url, artist.name, **kwargs)
        
        return artist

    def fetch_label(self, source: Source, stop_at_level: int = 1) -> Label:
        return Label()
    
    def download_song_to_target(self, source: Source, target: Target, desc: str = None) -> DownloadResult:
        """
        https://musify.club/track/im-in-a-coffin-life-never-was-waste-of-skin-16360302
        https://musify.club/track/dl/16360302/im-in-a-coffin-life-never-was-waste-of-skin.mp3
        """
        endpoint = source.audio_url

        if source.audio_url is None:
            url: MusifyUrl = parse_url(source.url)
            if url.source_type != MusifyTypes.SONG:
                return DownloadResult(error_message=f"The url is not of the type Song: {source.url}")

            endpoint = f"https://musify.club/track/dl/{url.musify_id}/{url.name_without_id}.mp3"

            self.LOGGER.warning(f"The source has no audio link. Falling back to {endpoint}.")

        return self.stream_connection.stream_into(endpoint, target, raw_url=True, exclude_headers=["Host"], name=desc)
