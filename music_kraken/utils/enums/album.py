from enum import Enum


class AlbumStatus(Enum):
    """
    Enum class representing the possible statuses of an album.
    """
    UNRELEASED = "Unreleased"
    RELEASED = "Released"
    LEAKED = "Leaked"
    OFFICIAL = "Official"
    BOOTLEG = "Bootleg"


class AlbumType(Enum):
    """
    Enum class representing the possible types of an album.
    """
    STUDIO_ALBUM = "Studio Album"
    EP = "EP (Extended Play)"
    SINGLE = "Single"
    LIVE_ALBUM = "Live Album"
    COMPILATION_ALBUM = "Compilation Album"
    MIXTAPE = "Mixtape"
    DEMO = "Demo"
    OTHER = "Other"
