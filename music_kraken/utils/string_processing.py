from typing import Tuple, Union
from pathlib import Path
import string

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

    if string is None:
        return None

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


# comparisons
TITLE_THRESHOLD_LEVENSHTEIN = 1
UNIFY_TO = " "

ALLOWED_LENGTH_DISTANCE = 20


def unify_punctuation(to_unify: str) -> str:
    for char in string.punctuation:
        to_unify = to_unify.replace(char, UNIFY_TO)
    return to_unify

def hash_url(url: str) -> int:
    return url.strip().lower().lstrip("https://").lstrip("http://")


def remove_feature_part_from_track(title: str) -> str:
    if ")" != title[-1]:
        return title
    if "(" not in title:
        return title

    return title[:title.index("(")]


def modify_title(to_modify: str) -> str:
    to_modify = to_modify.strip()
    to_modify = to_modify.lower()
    to_modify = remove_feature_part_from_track(to_modify)
    to_modify = unify_punctuation(to_modify)
    return to_modify


def match_titles(title_1: str, title_2: str):
    title_1, title_2 = modify_title(title_1), modify_title(title_2)
    distance = jellyfish.levenshtein_distance(title_1, title_2)
    return distance > TITLE_THRESHOLD_LEVENSHTEIN, distance


def match_artists(artist_1, artist_2: str):
    if type(artist_1) == list:
        distances = []

        for artist_1_ in artist_1:
            match, distance = match_titles(artist_1_, artist_2)
            if not match:
                return match, distance

            distances.append(distance)
        return True, min(distances)
    return match_titles(artist_1, artist_2)

def match_length(length_1: int | None, length_2: int | None) -> bool:
    # returning true if either one is Null, because if one value is not known,
    # then it shouldn't be an attribute which could reject an audio source
    if length_1 is None or length_2 is None:
        return True
    return abs(length_1 - length_2) <= ALLOWED_LENGTH_DISTANCE

