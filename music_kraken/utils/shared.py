import random

from .path_manager import LOCATIONS
from .config import main_settings

DEBUG = True
DEBUG_LOGGING = DEBUG and True
DEBUG_YOUTUBE_INITIALIZING = DEBUG and False
DEBUG_PAGES = DEBUG and False

if DEBUG:
    print("DEBUG ACTIVE")


def get_random_message() -> str:
    return random.choice(main_settings['happy_messages'])


CONFIG_DIRECTORY = LOCATIONS.CONFIG_DIRECTORY

HIGHEST_ID = 2 ** main_settings['id_bits']

HELP_MESSAGE = """to search:
> s: {query or url}
> s: https://musify.club/release/some-random-release-183028492
> s: #a {artist} #r {release} #t {track}

to download:
> d: {option ids or direct url}
> d: 0, 3, 4
> d: 1
> d: https://musify.club/release/some-random-release-183028492

have fun :3""".strip()
