import jellyfish
import string

TITLE_THRESHOLD_LEVENSHTEIN = 1
UNIFY_TO = " "

ALLOWED_LENGTH_DISTANCE = 20


def unify_punctuation(to_unify: str) -> str:
    for char in string.punctuation:
        to_unify = to_unify.replace(char, UNIFY_TO)
    return to_unify


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
