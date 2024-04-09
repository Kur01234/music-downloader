from typing import Tuple, Union
from pathlib import Path

from transliterate.exceptions import LanguageDetectionError
from transliterate import translit
from pathvalidate import sanitize_filename


COMMON_TITLE_APPENDIX_LIST: Tuple[str, ...] = (
    "(official video)",
)


def unify(string: str) -> str:
    """
    returns a unified str, to make comparisons easy.
    a unified string has the following attributes:
     - is lowercase
    """

    try:
        string = translit(string, reversed=True)
    except LanguageDetectionError:
        pass

    return string.lower()


def fit_to_file_system(string: Union[str, Path]) -> Union[str, Path]:
    def fit_string(string: str) -> str:
        if string == "/":
            return "/"
        string = string.strip()

        while string[0] == ".":
            if len(string) == 0:
                return string

            string = string[1:]

        string = string.replace("/", "_").replace("\\", "_")
        string = sanitize_filename(string)
        return string

    if isinstance(string, Path):
        return Path(*(fit_string(part) for part in string.parts))
    else:
        return fit_string(string)


def clean_song_title(raw_song_title: str, artist_name: str) -> str:
    """
    This function cleans common naming "conventions" for non clean song titles, like the title of youtube videos
    
    cleans:

    - `artist - song` -> `song`
    - `song (Official Video)` -> `song`
    - ` song` -> `song`
    - `song (prod. some producer)`
    """
    raw_song_title = raw_song_title.strip()
    artist_name = artist_name.strip()

    # Clean official Video appendix
    for dirty_appendix in COMMON_TITLE_APPENDIX_LIST:
        if raw_song_title.lower().endswith(dirty_appendix):
            raw_song_title = raw_song_title[:-len(dirty_appendix)].strip()

    # Remove artist from the start of the title
    if raw_song_title.lower().startswith(artist_name.lower()):
        raw_song_title = raw_song_title[len(artist_name):].strip()

        if raw_song_title.startswith("-"):
            raw_song_title = raw_song_title[1:].strip()

    return raw_song_title.strip()

    
def comment(uncommented_string: str) -> str:
    _fragments = uncommented_string.split("\n")
    _fragments = ["# " + frag for frag in _fragments]
    return "\n".join(_fragments)

