from typing import TypedDict, List
from urllib.parse import ParseResult
from logging import Logger
from pathlib import Path

from ...path_manager import LOCATIONS
from ..config import Config
from ..attributes.attribute import Attribute
from ..attributes.special_attributes import SelectAttribute, PathAttribute, UrlAttribute


config = Config((
    Attribute(name="use_youtube_alongside_youtube_music", default_value=False, description="""If set to true, it will search youtube through invidious and piped,
despite a direct wrapper for the youtube music INNERTUBE api being implemented.
I my INNERTUBE api wrapper doesn't work, set this to true."""),
    UrlAttribute(name="invidious_instance", default_value="https://yt.artemislena.eu", description="""This is an attribute, where you can define the invidious instances,
the youtube downloader should use.
Here is a list of active ones: https://docs.invidious.io/instances/
Instances that use cloudflare or have source code changes could cause issues.
Hidden instances (.onion) will only work, when setting 'tor=true'."""),
    UrlAttribute(name="piped_instance", default_value="https://piped-api.privacy.com.de", description="""This is an attribute, where you can define the pioed instances,
the youtube downloader should use.
Here is a list of active ones: https://github.com/TeamPiped/Piped/wiki/Instances
Instances that use cloudflare or have source code changes could cause issues.
Hidden instances (.onion) will only work, when setting 'tor=true"""),
    Attribute(name="sleep_after_youtube_403", default_value=30, description="The time to wait, after youtube returned 403 (in seconds)"),
    Attribute(name="youtube_music_api_key", default_value="AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30", description="""This is the API key used by YouTube-Music internally.
Dw. if it is empty, Rachel will fetch it automatically for you <333
(she will also update outdated api keys/those that don't work)"""),
    Attribute(name="youtube_music_clean_data", default_value=True, description="If set to true, it exclusively fetches artists/albums/songs, not things like user channels etc."),
    UrlAttribute(name="youtube_url", default_value=[
        "https://www.youtube.com/",
        "https://www.youtu.be/",
        "https://music.youtube.com/",
    ], description="""This is used to detect, if an url is from youtube, or any alternativ frontend.
If any instance seems to be missing, run music kraken with the -f flag."""),
    Attribute(name="use_sponsor_block", default_value=True, description="Use sponsor block to remove adds or simmilar from the youtube videos."),

    Attribute(name="player_url", default_value="https://music.youtube.com/s/player/80b90bfd/player_ias.vflset/en_US/base.js", description="""
    This is needed to fetch videos without invidious
    """),
    Attribute(name="youtube_music_consent_cookies", default_value={
        "CONSENT": "PENDING+258"
    }, description="The cookie with the key CONSENT says to what stuff you agree. Per default you decline all cookies, but it honestly doesn't matter."),

    Attribute(name="youtube_music_innertube_context", default_value={
                "client": {
                    "hl": "en",
                    "gl": "DE",
                    "remoteHost": "87.123.241.77",
                    "deviceMake": "",
                    "deviceModel": "",
                    "visitorData": "CgtiTUxaTHpoXzk1Zyia59WlBg%3D%3D",
                    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
                    "clientName": "WEB_REMIX",
                    "clientVersion": "1.20230710.01.00",
                    "osName": "X11",
                    "osVersion": "",
                    "originalUrl": "https://music.youtube.com/",
                    "platform": "DESKTOP",
                    "clientFormFactor": "UNKNOWN_FORM_FACTOR",
                    "configInfo": {
                        "appInstallData": "",
                        "coldConfigData": "",
                        "coldHashData": "",
                        "hotHashData": ""
                    },
                    "userInterfaceTheme": "USER_INTERFACE_THEME_DARK",
                    "timeZone": "Atlantic/Jan_Mayen",
                    "browserName": "Firefox",
                    "browserVersion": "115.0",
                    "acceptHeader": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "deviceExperimentId": "ChxOekkxTmpnek16UTRNVFl4TkRrek1ETTVOdz09EJrn1aUGGJrn1aUG",
                    "screenWidthPoints": 584,
                    "screenHeightPoints": 939,
                    "screenPixelDensity": 1,
                    "screenDensityFloat": 1,
                    "utcOffsetMinutes": 120,
                    "musicAppInfo": {
                        "pwaInstallabilityStatus": "PWA_INSTALLABILITY_STATUS_UNKNOWN",
                        "webDisplayMode": "WEB_DISPLAY_MODE_BROWSER",
                        "storeDigitalGoodsApiSupportStatus": {
                            "playStoreDigitalGoodsApiSupportStatus": "DIGITAL_GOODS_API_SUPPORT_STATUS_UNSUPPORTED"
                        }
                    }
                },
                "user": { "lockedSafetyMode": False },
                "request": {
                    "useSsl": True,
                    "internalExperimentFlags": [],
                    "consistencyTokenJars": []
                },
                "adSignalsInfo": {
                    "params": []
                }
            }, description="Don't bother about this. It is something technical, but if you wanna change the innertube requests... go on."),
    Attribute(name="ytcfg", description="Please... ignore it.", default_value={})
), LOCATIONS.get_config_file("youtube"))


class SettingsStructure(TypedDict):
    use_youtube_alongside_youtube_music: bool
    invidious_instance: ParseResult
    piped_instance: ParseResult
    sleep_after_youtube_403: float
    youtube_music_api_key: str
    youtube_music_clean_data: bool
    youtube_url: List[ParseResult]
    use_sponsor_block: bool
    player_url: str
    youtube_music_innertube_context: dict
    youtube_music_consent_cookies: dict
    ytcfg: dict
