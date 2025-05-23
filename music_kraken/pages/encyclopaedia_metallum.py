from collections import defaultdict
from typing import List, Optional, Dict, Type, Union
from bs4 import BeautifulSoup
import pycountry
from urllib.parse import urlparse, urlencode

from ..connection import Connection
from ..utils.config import logging_settings
from .abstract import Page
from ..utils.enums import SourceType, ALL_SOURCE_TYPES
from ..utils.enums.album import AlbumType
from ..utils.support_classes.query import Query
from ..objects import (
    Lyrics,
    Artist,
    Source,
    Song,
    Album,
    ID3Timestamp,
    FormattedText,
    Label,
    Options,
    DatabaseObject
)
from ..utils.shared import DEBUG
from ..utils import dump_to_file



ALBUM_TYPE_MAP: Dict[str, AlbumType] = defaultdict(lambda: AlbumType.OTHER, {
    "Full-length": AlbumType.STUDIO_ALBUM,
    "Single": AlbumType.SINGLE,
    "EP": AlbumType.EP,
    "Demo": AlbumType.DEMO,
    "Video": AlbumType.OTHER,
    "Live album": AlbumType.LIVE_ALBUM,
    "Compilation": AlbumType.COMPILATION_ALBUM
})

URL_SITE = 'https://www.metal-archives.com/'
URL_IMAGES = 'https://www.metal-archives.com/images/'
URL_CSS = 'https://www.metal-archives.com/css/'


def _song_from_json(artist_html=None, album_html=None, release_type=None, title=None, lyrics_html=None) -> Song:
    song_id = None
    if lyrics_html is not None:
        soup = BeautifulSoup(lyrics_html, 'html.parser')
        anchor = soup.find('a')
        raw_song_id = anchor.get('id')
        song_id = raw_song_id.replace("lyricsLink_", "")

    return Song(
        title=title,
        artist_list=[
            _artist_from_json(artist_html=artist_html)
        ],
        album_list=[
            _album_from_json(album_html=album_html, release_type=release_type, artist_html=artist_html)
        ],
        source_list=[
            Source(ALL_SOURCE_TYPES.ENCYCLOPAEDIA_METALLUM, song_id)
        ]
    )


def _artist_from_json(artist_html=None, genre=None, country=None) -> Artist:
    """
    TODO parse the country to a standard
    """
    # parse the html
    # parse the html for the band name and link on metal-archives
    soup = BeautifulSoup(artist_html, 'html.parser')
    anchor = soup.find('a')
    artist_name = anchor.text
    artist_url = anchor.get('href')
    artist_id = artist_url.split("/")[-1]

    anchor.decompose()
    strong = soup.find('strong')
    if strong is not None:
        strong.decompose()
        akronyms_ = soup.text[2:-2].split(', ')

    return Artist(
        name=artist_name,
        source_list=[
            Source(ALL_SOURCE_TYPES.ENCYCLOPAEDIA_METALLUM, artist_url)
        ]
    )


def _album_from_json(album_html=None, release_type=None, artist_html=None) -> Album:
    # parse the html
    # <a href="https://www.metal-archives.com/albums/Ghost_Bath/Self_Loather/970834">Self Loather</a>'
    soup = BeautifulSoup(album_html, 'html.parser')
    anchor = soup.find('a')
    album_name = anchor.text.strip()
    album_url = anchor.get('href')
    album_id = album_url.split("/")[-1]

    album_type = ALBUM_TYPE_MAP[release_type.strip()]

    return Album(
        title=album_name,
        album_type=album_type,
        source_list=[
            Source(ALL_SOURCE_TYPES.ENCYCLOPAEDIA_METALLUM, album_url)
        ],
        artist_list=[
            _artist_from_json(artist_html=artist_html)
        ]
    )


def create_grid(
        tableOrId: str = "#searchResultsSong",
        nbrPerPage: int = 200,
        ajaxUrl: str = "search/ajax-advanced/searching/songs/?songTitle=high&bandName=&releaseTitle=&lyrics=&genre=",
        extraOptions: dict = None
):
    """
    function createGrid(tableOrId, nbrPerPage, ajaxUrl, extraOptions) {
        var table = null;
        if (typeof tableOrId == "string") {
            table = $(tableOrId);
        } else {
            table = tableOrId;
        }
        if (ajaxUrl == undefined) {
            ajaxUrl = null;
        }
        var options = {
            bAutoWidth: false,
            bFilter: false,
            bLengthChange: false,
            bProcessing: true,
            bServerSide: ajaxUrl != null,
            iDisplayLength: nbrPerPage,
            sAjaxSource: URL_SITE + ajaxUrl,
            sPaginationType: 'full_numbers',
            sDom: 'ipl<"block_spacer_5"><"clear"r>f<t>rip',
            oLanguage: {
                sProcessing: 'Loading...',
                sEmptyTable: 'No records to display.',
                sZeroRecords: 'No records found.'
            },
            "fnDrawCallback": autoScrollUp
        };
        if (typeof extraOptions == "object") {
            for (var key in extraOptions) {
                options[key] = extraOptions[key];
                if (key == 'fnDrawCallback') {
                    var callback = options[key];
                    options[key] = function(o) {
                        autoScrollUp(o);
                        callback(o);
                    }
                }
            }
        }
        return table.dataTable(options);
    }

    :return:
    """

    def onDrawCallback(o):
        """
        this gets executed once the ajax request is done
        :param o:
        :return:
        """

    extraOptions = extraOptions or {
        "bSort": False,
        "oLanguage": {
            "sProcessing": 'Searching, please wait...',
            "sEmptyTable": 'No matches found. Please try with different search terms.'
         }
    }
    options = {
        "bAutoWidth": False,
        "bFilter": False,
        "bLengthChange": False,
        "bProcessing": True,
        "bServerSide": ajaxUrl is not None,
        "iDisplayLength": nbrPerPage,
        "sAjaxSource": URL_SITE + ajaxUrl,
        "sPaginationType": 'full_numbers',
        "sDom": 'ipl<"block_spacer_5"><"clear"r>f<t>rip',
        "oLanguage": {
            "sProcessing": 'Loading...',
            "sEmptyTable": 'No records to display.',
            "sZeroRecords": 'No records found.'
        },
        "fnDrawCallback": onDrawCallback
    }

    for key, value in extraOptions.items():
        options[key] = value
        if key == 'fnDrawCallback':
            callback = options[key]
            options[key] = lambda o: onDrawCallback(o) and callback(o)

    # implement jquery datatable


class EncyclopaediaMetallum(Page):
    SOURCE_TYPE = ALL_SOURCE_TYPES.ENCYCLOPAEDIA_METALLUM
    LOGGER = logging_settings["metal_archives_logger"]
    
    def __init__(self, **kwargs):
        self.connection: Connection = Connection(
            host="https://www.metal-archives.com/",
            logger=self.LOGGER,
            module=type(self).__name__
        )
        
        super().__init__(**kwargs)

    def song_search(self, song: Song) -> List[Song]:
        endpoint = "https://www.metal-archives.com/search/ajax-advanced/searching/songs/?"
        """
        endpoint = "https://www.metal-archives.com/search/ajax-advanced/searching/songs/?songTitle={song}&bandName={" \
                   "artist}&releaseTitle={album}&lyrics=&genre=&sEcho=1&iColumns=5&sColumns=&iDisplayStart=0" \
                   "&iDisplayLength=200&mDataProp_0=0&mDataProp_1=1&mDataProp_2=2&mDataProp_3=3&mDataProp_4=4&_" \
                   "=1674550595663"
        """

        """
        The difficult question I am facing is, that if I try every artist, with every song, with every album,
        I end up with a quadratic runtime complecety O(n^2), where every step means one web request.
        
        This.
        Is not good.
        """

        search_params = {
            "songTitle": song.title,
            "bandName": "*",
            "releaseTitle": "*",
            "lyrics": "",
            "genre": "",
            "sEcho": 1,
            "iColumns": 5,
            "sColumns": "",
            "iDisplayStart": 0,
            "iDisplayLength": 200,
            "mDataProp_0": 0,
            "mDataProp_1": 1,
            "mDataProp_2": 2,
            "mDataProp_3": 3,
            "mDataProp_4": 4,
            "_": 1705946986092
        }
        referer_params = {
            "songTitle": song.title,
            "bandName": "*",
            "releaseTitle": "*",
            "lyrics": "",
            "genre": "",
        }

        urlencode(search_params)

        song_title = song.title.strip()
        album_titles = ["*"] if song.album_collection.empty else [album.title.strip() for album in song.album_collection]
        artist_titles = ["*"] if song.artist_collection.empty else [artist.name.strip() for artist in song.artist_collection]


        search_results = []

        for artist in artist_titles:
            for album in album_titles:
                _search = search_params.copy()
                _referer_params = referer_params.copy()
                _search["bandName"] = _referer_params["bandName"] = artist
                _search["releaseTitle"] = _referer_params["releaseTitle"] = album

                r = self.connection.get(endpoint + urlencode(_search), headers={
                    "Referer": "https://www.metal-archives.com/search/advanced/searching/songs?" + urlencode(_referer_params),
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "X-Requested-With": "XMLHttpRequest",
                }, name="song_search")

                if r is None:
                    return []

                search_results.extend(_song_from_json(
                    artist_html=raw_song[0],
                    album_html=raw_song[1],
                    release_type=raw_song[2],
                    title=raw_song[3],
                    lyrics_html=raw_song[4]
                ) for raw_song in r.json()['aaData'])

        return search_results

    def album_search(self, album: Album) -> List[Album]:
        endpoint = "https://www.metal-archives.com/search/ajax-advanced/searching/albums/?"

        search_params = {
            "bandName": "*",
            "releaseTitle": album.title.strip(),
            "releaseYearFrom": "",
            "releaseMonthFrom": "",
            "releaseYearTo": "",
            "releaseMonthTo": "",
            "country": "",
            "location": "",
            "releaseLabelName": "",
            "releaseCatalogNumber": "",
            "releaseIdentifiers": "",
            "releaseRecordingInfo": "",
            "releaseDescription": "",
            "releaseNotes": "",
            "genre": "",
            "sEcho": 1,
            "iColumns": 3,
            "sColumns": "",
            "iDisplayStart": 0,
            "iDisplayLength": 200,
            "mDataProp_0": 0,
            "mDataProp_1": 1,
            "mDataProp_2": 2,
            "_": 1705946986092
        }
        referer_params = {
            "bandName": "*",
            "releaseTitle": album.title.strip(),
        }

        album_title = album.title
        artist_titles = ["*"] if album.artist_collection.empty else [artist.name.strip() for artist in album.artist_collection]

        search_results = []

        for artist in artist_titles:
            _search = search_params.copy()
            _referer_params = referer_params.copy()
            _search["bandName"] = _referer_params["bandName"] = artist

            r = self.connection.get(endpoint + urlencode(_search), headers={
                "Referer": "https://www.metal-archives.com/search/advanced/searching/albums?" + urlencode(_referer_params),
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",

            })

            #r = self.connection.get(endpoint.format(artist=artist, album=album_title))
            if r is None:
                return []

            search_results.extend(_album_from_json(
                artist_html=raw_album[0],
                album_html=raw_album[1],
                release_type=raw_album[2]
            ) for raw_album in r.json()['aaData'])

    def artist_search(self, artist: Artist) -> List[Artist]:
        endpoint = "https://www.metal-archives.com/search/ajax-advanced/searching/bands/?"

        search_params = {
            "bandName": artist.name.strip(),
            "genre": "",
            "country": "",
            "yearCreationFrom": "",
            "yearCreationTo": "",
            "bandNotes": "",
            "status": "",
            "themes": "",
            "location": "",
            "bandLabelName": "",
            "sEcho": 1,
            "iColumns": 3,
            "sColumns": "",
            "iDisplayStart": 0,
            "iDisplayLength": 200,
            "mDataProp_0": 0,
            "mDataProp_1": 1,
            "mDataProp_2": 2,
            "_": 1705946986092
        }

        r = self.connection.get(endpoint + urlencode(search_params), headers={
            "Referer": "https://www.metal-archives.com/search/advanced/searching/bands?" + urlencode({"bandName": artist.name.strip()}),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }, name="artist_search.json")

        if r is None:
            return []

        data_key = 'aaData'
        parsed_data = r.json()
        if data_key not in parsed_data:
            return []

        return [
            _artist_from_json(artist_html=raw_artist[0], genre=raw_artist[1], country=raw_artist[2])
            for raw_artist in r.json()['aaData']
        ]

    def general_search(self, query: str) -> List[DatabaseObject]:
        """
        Searches the default endpoint from metal archives, which intern searches only
        for bands, but it is the default, thus I am rolling with it
        """
        endpoint = "https://www.metal-archives.com/search/ajax-band-search/?field=name&query={query}&sEcho=1&iColumns=3&sColumns=&iDisplayStart=0&iDisplayLength=200&mDataProp_0=0&mDataProp_1=1&mDataProp_2=2"

        r = self.connection.get(endpoint.format(query=query))
        if r is None:
            return []

        return [
            _artist_from_json(artist_html=raw_artist[0], genre=raw_artist[1], country=raw_artist[2])
            for raw_artist in r.json()['aaData']
        ]

    def _fetch_artist_discography(self, ma_artist_id: str) -> List[Album]:
        discography_url = "https://www.metal-archives.com/band/discography/id/{}/tab/all"

        # make the request
        r = self.connection.get(discography_url.format(ma_artist_id))
        if r is None:
            return []
        soup = self.get_soup_from_response(r)

        discography = []

        tbody_soup = soup.find('tbody')
        for tr_soup in tbody_soup.find_all('tr'):
            td_list = tr_soup.findChildren(recursive=False)

            album_soup = td_list[0]
            album_name = album_soup.text
            album_url = album_soup.find('a').get('href')
            album_id = album_url.split('/')[-1]
            raw_album_type = td_list[1].text
            album_year = td_list[2].text
            date_obj = None
            try:
                date_obj = ID3Timestamp(year=int(album_year))
            except ValueError():
                pass

            discography.append(
                Album(
                    title=album_name,
                    date=date_obj,
                    album_type=ALBUM_TYPE_MAP[raw_album_type],
                    source_list=[Source(self.SOURCE_TYPE, album_url)]
                )
            )

        return discography

    def _fetch_artist_sources(self, ma_artist_id: str) -> List[Source]:
        sources_url = "https://www.metal-archives.com/link/ajax-list/type/band/id/{}"
        r = self.connection.get(sources_url.format(ma_artist_id))
        if r is None:
            return []

        soup = self.get_soup_from_response(r)

        if DEBUG:
            dump_to_file(f"ma_artist_sources_{ma_artist_id}.html", soup.prettify(), exit_after_dump=False)

        if soup.find("span", {"id": "noLinks"}) is not None:
            return []

        source_list = []

        link_table: BeautifulSoup = soup.find("table", {"id": "linksTablemain"})
        if link_table is not None:
            for tr in link_table.find_all("tr"):
                anchor: BeautifulSoup = tr.find("a")
                if anchor is None:
                    continue

                href = anchor["href"]
                if href is not None:
                    source_list.append(Source.match_url(href, referrer_page=self.SOURCE_TYPE))

        # The following code is only legacy code, which I just kep because it doesn't harm.
        # The way ma returns sources changed.
        artist_source = soup.find("div", {"id": "band_links"})

        merchandice_source = soup.find("div", {"id": "band_links_Official_merchandise"})
        label_source = soup.find("div", {"id": "band_links_Labels"})



        if artist_source is not None:
            for tr in artist_source.find_all("td"):
                a = tr.find("a")
                url = a.get("href")
                if url is None:
                    continue

                source_list.append(Source.match_url(url, referrer_page=self.SOURCE_TYPE))
                
        return source_list

    def _parse_artist_attributes(self, artist_soup: BeautifulSoup) -> Artist:
        name: str = None
        country: pycountry.Countrie = None
        formed_in_year: int = None
        genre: str = None
        lyrical_themes: List[str] = []
        label_name: str = None
        label_url: str = None
        source_list: List[Source] = []

        title_soup: BeautifulSoup = artist_soup.find("title")
        if title_soup is not None:
            bad_name_substring = " - Encyclopaedia Metallum: The Metal Archives"
            title_text = title_soup.get_text()
            if title_text.count(bad_name_substring) == 1:
                name = title_text.replace(bad_name_substring, "")
            else:
                self.LOGGER.debug(f"the title of the page is \"{title_text}\"")

        """
        TODO
        Implement the bandpictures and logos that can be gotten with the elements
        <a class="image" id="photo" title="Ghost Bath"...
        <a class="image" id="logo" title="Ghost Bath"...
        where the titles are the band name
        """
        image_container_soup: BeautifulSoup = artist_soup.find(id="band_sidebar")
        if image_container_soup is not None:
            logo_soup = image_container_soup.find(id="logo")
            if logo_soup is not None:
                logo_title = logo_soup.get("title")
                if logo_title is not None:
                    name = logo_title.strip()

            band_pictures = image_container_soup.find(id="photo")
            if band_pictures is not None:
                band_picture_title = logo_soup.get("title")
                if band_picture_title is not None:
                    name = band_picture_title.strip()

        for h1_band_name_soup in artist_soup.find_all("h1", {"class": "band_name"}):
            anchor: BeautifulSoup = h1_band_name_soup.find("a")
            if anchor is None:
                continue

            href = anchor.get("href")
            if href is not None:
                source_list.append(Source(self.SOURCE_TYPE, href))

            name = anchor.get_text(strip=True)

        band_stat_soup = artist_soup.find("div", {"id": "band_stats"})
        for dl_soup in band_stat_soup.find_all("dl"):
            for title, data in zip(dl_soup.find_all("dt"), dl_soup.find_all("dd")):
                title_text = title.text

                if "Country of origin:" == title_text:
                    href = data.find('a').get('href')
                    country = pycountry.countries.get(alpha_2=href.split("/")[-1])
                    continue

                # not needed: Location: Minot, North Dakota

                """
                TODO
                status: active
                need to do enums for that and add it to object
                """

                if "Formed in:" == title_text:
                    if not data.text.isnumeric():
                        continue
                    formed_in_year = int(data.text)
                    continue
                if "Genre:" == title_text:
                    genre = data.text
                    continue
                if "Lyrical themes:" == title_text:
                    lyrical_themes = data.text.split(", ")
                    continue
                if "Current label:" == title_text:
                    label_name = data.text
                    label_anchor = data.find("a")
                    label_url = None
                    if label_anchor is not None:
                        label_url = label_anchor.get("href")
                        label_id = None
                        if type(label_url) is str and "/" in label_url:
                            label_id = label_url.split("/")[-1]

                """
                TODO
                years active: 2012-present
                process this and add field to class
                """

        return Artist(
            name=name,
            country=country,
            formed_in=ID3Timestamp(year=formed_in_year),
            general_genre=genre,
            lyrical_themes=lyrical_themes,
            label_list=[
                Label(
                    name=label_name,
                    source_list=[
                        Source(self.SOURCE_TYPE, label_url)
                    ]
                )
            ],
            source_list=source_list
        )

    def _fetch_artist_attributes(self, url: str) -> Artist:
        r = self.connection.get(url)
        if r is None:
            return Artist()
        soup: BeautifulSoup = self.get_soup_from_response(r)

        return self._parse_artist_attributes(artist_soup=soup)

    def _fetch_band_notes(self, ma_artist_id: str) -> Optional[FormattedText]:
        endpoint = "https://www.metal-archives.com/band/read-more/id/{}"

        # make the request
        r = self.connection.get(endpoint.format(ma_artist_id))
        if r is None:
            return FormattedText()

        return FormattedText(html=r.text)

    def fetch_artist(self, source: Source, stop_at_level: int = 1) -> Artist:
        """
        What it could fetch, and what is implemented:

        [x] https://www.metal-archives.com/bands/Ghost_Bath/3540372489
        [x] https://www.metal-archives.com/band/discography/id/3540372489/tab/all
        [] reviews: https://www.metal-archives.com/review/ajax-list-band/id/3540372489/json/1?sEcho=1&iColumns=4&sColumns=&iDisplayStart=0&iDisplayLength=200&mDataProp_0=0&mDataProp_1=1&mDataProp_2=2&mDataProp_3=3&iSortCol_0=3&sSortDir_0=desc&iSortingCols=1&bSortable_0=true&bSortable_1=true&bSortable_2=true&bSortable_3=true&_=1675155257133
        [] simmilar: https://www.metal-archives.com/band/ajax-recommendations/id/3540372489
        [x] sources: https://www.metal-archives.com/link/ajax-list/type/band/id/3540372489
        [x] band notes: https://www.metal-archives.com/band/read-more/id/3540372489
        """

        artist = self._fetch_artist_attributes(source.url)

        artist_id = source.url.split("/")[-1]

        artist_sources = self._fetch_artist_sources(artist_id)
        artist.source_collection.extend(artist_sources)

        band_notes = self._fetch_band_notes(artist_id)
        if band_notes is not None:
            artist.notes = band_notes

        discography: List[Album] = self._fetch_artist_discography(artist_id)
        artist.album_collection.extend(discography)

        return artist

    def _parse_album_track_row(self, track_row: BeautifulSoup) -> Song:
        """
        <tr class="even">
            <td width="20"><a class="anchor" name="5948442"> </a>1.</td>        # id and tracksort
            <td class="wrapWords">Convince Me to Bleed</td>                     # name
            <td align="right">03:40</td>                                        # length
            <td nowrap="nowrap"> 
            <a href="#5948442" id="lyricsButton5948442" onclick="toggleLyrics('5948442'); return false;">Show lyrics</a>
            </td>
        </tr>
        """
        
        row_list = track_row.find_all(recursive=False)

        source_list: List[Source] = []

        track_sort_soup = row_list[0]
        track_sort = int(track_sort_soup.text[:-1])
        track_id = track_sort_soup.find("a").get("name").strip()
        
        if track_row.find("a", {"href": f"#{track_id}"}) is not None:
            source_list.append(Source(self.SOURCE_TYPE, track_id))

        title = row_list[1].text.strip()

        length = None

        duration_stamp = row_list[2].text
        if ":" in duration_stamp:
            minutes, seconds = duration_stamp.split(":")
            length = (int(minutes) * 60 + int(seconds)) * 1000  # in milliseconds

        return Song(
            title=title,
            length=length,
            tracksort=track_sort,
            source_list=source_list
        )
        
    def _parse_album_attributes(self, album_soup: BeautifulSoup, stop_at_level: int = 1) -> Album:
        tracklist: List[Song] = []
        artist_list = []
        album_name: str = None
        source_list: List[Source] = []
        
        def _parse_album_info(album_info_soup: BeautifulSoup):
            nonlocal artist_list
            nonlocal album_name
            nonlocal source_list
            
            if album_info_soup is None:
                return
            
            album_soup_list = album_info_soup.find_all("h1", {"class": "album_name"})
            if len(album_soup_list) == 1:
                anchor: BeautifulSoup = album_soup_list[0].find("a")
                
                href = anchor.get("href")
                if href is not None:
                    source_list.append(Source(self.SOURCE_TYPE, href.strip()))
                    
                album_name = anchor.get_text(strip=True)
                
            elif len(album_soup_list) > 1:
                self.LOGGER.debug("there are more than 1 album soups")
                
            
            artist_soup_list = album_info_soup.find_all("h2", {"class": "band_name"})
            if len(artist_soup_list) == 1:
                for anchor in artist_soup_list[0].find_all("a"):
                    artist_sources: List[Source] = []
                    
                    href = anchor.get("href")
                    if href is not None:
                        artist_sources.append(Source(self.SOURCE_TYPE, href.strip()))
                        
                    artist_name = anchor.get_text(strip=True)
                    
                    artist_list.append(Artist(
                        name=artist_name,
                        source_list=artist_sources
                    ))
                
            elif len(artist_soup_list) > 1:
                self.LOGGER.debug("there are more than 1 artist soups")
        
        _parse_album_info(album_info_soup=album_soup.find(id="album_info"))
        
        tracklist_soup = album_soup.find("table", {"class": "table_lyrics"}).find("tbody")
        for track_soup in tracklist_soup.find_all("tr", {"class": ["even", "odd"]}):
            tracklist.append(self._parse_album_track_row(track_row=track_soup))

        return Album(
            title=album_name,
            source_list=source_list,
            artist_list=artist_list,
            song_list=tracklist
        )

    def fetch_album(self, source: Source, stop_at_level: int = 1) -> Album:
        """
        I am preeeety sure I can get way more data than... nothing from there

        :param source:
        :param stop_at_level:
        :return:
        """

        # <table class="display table_lyrics

        r = self.connection.get(source.url)
        if r is None:
            return Album()

        soup = self.get_soup_from_response(r)
        
        album = self._parse_album_attributes(soup, stop_at_level=stop_at_level)       
        return album
    
    def _fetch_lyrics(self, song_id: str) -> Optional[Lyrics]:
        """
        function toggleLyrics(songId) {
            var lyricsRow = $('#song' + songId);
            lyricsRow.toggle();
            var lyrics = $('#lyrics_' + songId);
            if (lyrics.html() == '(loading lyrics...)') {
                var realId = songId;
                if(!$.isNumeric(songId.substring(songId.length -1, songId.length))) {
                    realId = songId.substring(0, songId.length -1);
                }
                lyrics.load(URL_SITE + "release/ajax-view-lyrics/id/" + realId);
            }
            // toggle link
            var linkLabel = "lyrics";
            $("#lyricsButton" + songId).text(lyricsRow.css("display") == "none" ? "Show " + linkLabel : "Hide " + linkLabel);
            return false;
        }
        """
        if song_id is None:
            return None
        
        endpoint = "https://www.metal-archives.com/release/ajax-view-lyrics/id/{id}".format(id=song_id)
        
        r = self.connection.get(endpoint)
        if r is None:
            return None
        
        return Lyrics(
            text=FormattedText(html=r.text),
            language=pycountry.languages.get(alpha_2="en"),
            source_list=[
                Source(self.SOURCE_TYPE, endpoint)
            ]
        )

    def fetch_song(self, source: Source, stop_at_level: int = 1) -> Song:
        song_id = source.url
        
        return Song(
            lyrics_list=[
                self._fetch_lyrics(song_id=song_id)
            ]
        )

    def get_source_type(self, source: Source):
        if self.SOURCE_TYPE != source.source_type:
            return None
        
        url = source.url
        if url is None:
            return None
        
        parsed_url = urlparse(url)
        path: List[str] = parsed_url.path.split("/")
        
        if "band" in path:
            return Artist
        if "bands" in path:
            return Artist
        
        if "albums" in path:
            return Album
        
        if "labels" in path:
            return Label
        
        return None
