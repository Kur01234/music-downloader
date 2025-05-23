import random
from dotenv import load_dotenv
from pathlib import Path
import os


from .path_manager import LOCATIONS
from .config import main_settings

if not load_dotenv(Path(__file__).parent.parent.parent / ".env"):
    load_dotenv(Path(__file__).parent.parent.parent / ".env.example")

__stage__ = os.getenv("STAGE", "prod")

DEBUG = (__stage__ == "dev") and True
DEBUG_LOGGING = DEBUG and False
DEBUG_TRACE = DEBUG and True
DEBUG_OBJECT_TRACE = DEBUG and False
DEBUG_OBJECT_TRACE_CALLSTACK = DEBUG_OBJECT_TRACE and False
DEBUG_YOUTUBE_INITIALIZING = DEBUG and False
DEBUG_PAGES = DEBUG and False
DEBUG_DUMP = DEBUG and True
DEBUG_PRINT_ID = DEBUG and True

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

# regex pattern
URL_PATTERN = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
INT_PATTERN = r"^\d*$"
FLOAT_PATTERN = r"^[\d|\,|\.]*$"
