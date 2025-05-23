from dataclasses import dataclass, field
from typing import Set

from ..utils.config import main_settings
from ..utils.enums.album import AlbumType


@dataclass
class FetchOptions:
    download_all: bool = False
    album_type_blacklist: Set[AlbumType] = field(default_factory=lambda: set(AlbumType(a) for a in main_settings["album_type_blacklist"]))


@dataclass
class DownloadOptions:
    download_all: bool = False
    album_type_blacklist: Set[AlbumType] = field(default_factory=lambda: set(AlbumType(a) for a in main_settings["album_type_blacklist"]))

    download_again_if_found: bool = False
    process_audio_if_found: bool = False
    process_metadata_if_found: bool = True
