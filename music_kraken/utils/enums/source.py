from enum import Enum


class SourceTypes(Enum):
    SONG = "song"
    ALBUM = "album"
    ARTIST = "artist"
    LYRICS = "lyrics"


class SourcePages(Enum):
    YOUTUBE = "youtube"
    MUSIFY = "musify"
    YOUTUBE_MUSIC = "youtube music"
    GENIUS = "genius"
    MUSICBRAINZ = "musicbrainz"
    ENCYCLOPAEDIA_METALLUM = "encyclopaedia metallum"
    BANDCAMP = "bandcamp"
    DEEZER = "deezer"
    SPOTIFY = "spotify"

    # This has nothing to do with audio, but bands can be here
    WIKIPEDIA = "wikipedia"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"     # I will use nitter though lol
    MYSPACE = "myspace"     # Yes somehow this ancient site is linked EVERYWHERE

    MANUAL = "manual"
    
    PRESET = "preset"

    @classmethod
    def get_homepage(cls, attribute) -> str:
        homepage_map = {
            cls.YOUTUBE: "https://www.youtube.com/",
            cls.MUSIFY: "https://musify.club/",
            cls.MUSICBRAINZ: "https://musicbrainz.org/",
            cls.ENCYCLOPAEDIA_METALLUM: "https://www.metal-archives.com/",
            cls.GENIUS: "https://genius.com/",
            cls.BANDCAMP: "https://bandcamp.com/",
            cls.DEEZER: "https://www.deezer.com/",
            cls.INSTAGRAM: "https://www.instagram.com/",
            cls.FACEBOOK: "https://www.facebook.com/",
            cls.SPOTIFY: "https://open.spotify.com/",
            cls.TWITTER: "https://twitter.com/",
            cls.MYSPACE: "https://myspace.com/",
            cls.WIKIPEDIA: "https://en.wikipedia.org/wiki/Main_Page"
        }
        return homepage_map[attribute]