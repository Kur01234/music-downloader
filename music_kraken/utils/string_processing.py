from typing import Tuple, Union, Optional
from pathlib import Path
import string
from functools import lru_cache

from transliterate.exceptions import LanguageDetectionError
from transliterate import translit
from pathvalidate import sanitize_filename
from urllib.parse import urlparse, ParseResult, parse_qs


COMMON_TITLE_APPENDIX_LIST: Tuple[str, ...] = (
    "(official video)",
)
OPEN_BRACKETS = "(["
CLOSE_BRACKETS = ")]"
DISALLOWED_SUBSTRING_IN_BRACKETS = ("official", "video", "audio", "lyrics", "prod", "remix", "ft", "feat", "ft.", "feat.")

@lru_cache
def unify(string: str) -> str:
    """
    returns a unified str, to make comparisons easy.
    a unified string has the following attributes:
    - is lowercase
    - is transliterated to Latin characters from e.g. Cyrillic
    """

    if string is None:
        return None

    try:
        string = translit(string, reversed=True)
    except LanguageDetectionError:
        pass
    
    string = unify_punctuation(string)
    return string.lower().strip()


def fit_to_file_system(string: Union[str, Path], hidden_ok: bool = False) -> Union[str, Path]:
    def fit_string(string: str) -> str:
        nonlocal hidden_ok
        
        if string == "/":
            return "/"
        string = string.strip()

        while string[0] == "." and not hidden_ok:
            if len(string) == 0:
                return string

            string = string[1:]

        string = string.replace("/", "_").replace("\\", "_")

        try:
            string = translit(string, reversed=True)
        except LanguageDetectionError:
            pass
        
        string = sanitize_filename(string)

        return string

    if isinstance(string, Path):
        return Path(*(fit_string(part) for part in string.parts))
    else:
        return fit_string(string)


@lru_cache(maxsize=128)
def clean_song_title(raw_song_title: str, artist_name: Optional[str] = None) -> str:
    """
    This function cleans common naming "conventions" for non clean song titles, like the title of youtube videos
    
    cleans:

    - `artist - song` -> `song`
    - `song (Official Video)` -> `song`
    - ` song` -> `song`
    - `song (prod. some producer)`
    """
    raw_song_title = raw_song_title.strip()

    # Clean official Video appendix
    for dirty_appendix in COMMON_TITLE_APPENDIX_LIST:
        if raw_song_title.lower().endswith(dirty_appendix):
            raw_song_title = raw_song_title[:-len(dirty_appendix)].strip()

    # remove brackets and their content if they contain disallowed substrings
    for open_bracket, close_bracket in zip(OPEN_BRACKETS, CLOSE_BRACKETS):
        if open_bracket not in raw_song_title or close_bracket not in raw_song_title:
            continue
        
        start = 0

        while True:
            try:
                open_bracket_index = raw_song_title.index(open_bracket, start)
            except ValueError:
                break
            try:
                close_bracket_index = raw_song_title.index(close_bracket, open_bracket_index + 1)
            except ValueError:
                break

            substring = raw_song_title[open_bracket_index + 1:close_bracket_index]
            if any(disallowed_substring in substring.lower() for disallowed_substring in DISALLOWED_SUBSTRING_IN_BRACKETS):
                raw_song_title = raw_song_title[:open_bracket_index] + raw_song_title[close_bracket_index + 1:]
            else:
                start = close_bracket_index + 1

    # everything that requires the artist name
    if artist_name is not None:
        artist_name = artist_name.strip()

        # Remove artist from the start of the title
        if raw_song_title.lower().startswith(artist_name.lower()):

            possible_new_name = raw_song_title[len(artist_name):].strip()

            for char in ("-", "–", ":", "|"):
                if possible_new_name.startswith(char):
                    raw_song_title = possible_new_name[1:].strip()
                    break

    return raw_song_title.strip()

    
def comment(uncommented_string: str) -> str:
    _fragments = uncommented_string.split("\n")
    _fragments = ["# " + frag for frag in _fragments]
    return "\n".join(_fragments)


# comparisons
TITLE_THRESHOLD_LEVENSHTEIN = 1
UNIFY_TO = " "

ALLOWED_LENGTH_DISTANCE = 20


def unify_punctuation(to_unify: str, unify_to: str = UNIFY_TO) -> str:
    for char in string.punctuation:
        to_unify = to_unify.replace(char, unify_to)
    return to_unify

@lru_cache(maxsize=128)
def hash_url(url: Union[str, ParseResult]) -> str:
    if isinstance(url, str): 
        url = urlparse(url)

    unify_to = "-"

    def unify_part(part: str) -> str:
        nonlocal unify_to
        return unify_punctuation(part.lower(), unify_to=unify_to).strip(unify_to)

    # netloc
    netloc = unify_part(url.netloc)
    if netloc.startswith("www" + unify_to):
        netloc = netloc[3 + len(unify_to):]

    # query
    query = url.query
    query_dict: Optional[dict] = None
    try:
        query_dict: dict = parse_qs(url.query, strict_parsing=True)
    except ValueError:
        # the query couldn't be parsed
        pass

    if isinstance(query_dict, dict):
        # sort keys alphabetically
        query = ""
        for key, value in sorted(query_dict.items(), key=lambda i: i[0]):
            query += f"{key.strip()}-{''.join(i.strip() for i in value)}"

    r = f"{netloc}_{unify_part(url.path)}_{unify_part(query)}"
    r = r.lower().strip()
    return r


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

def shorten_display_url(url: str, max_length: int = 150, chars_at_end: int = 4, shorten_string: str = "[...]") -> str:
    if len(url) <= max_length + chars_at_end + len(shorten_string):
        return url
    
    return url[:max_length] + shorten_string + url[-chars_at_end:]
