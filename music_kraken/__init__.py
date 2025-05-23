import logging
import gc
import sys
from pathlib import Path

from rich.logging import RichHandler
from rich.console import Console

from .utils.shared import DEBUG, DEBUG_LOGGING
from .utils.config import logging_settings, main_settings, read_config

read_config()

console: Console = Console()
def init_logging():
    log_file = main_settings['log_file']

    if log_file.is_file():
        last_log_file = Path(log_file.parent, "prev." + log_file.name)

        with log_file.open("r", encoding="utf-8") as current_file:
            with last_log_file.open("w", encoding="utf-8") as last_file:
                last_file.write(current_file.read())

    rich_handler = RichHandler(rich_tracebacks=True, console=console)
    rich_handler.setLevel(logging_settings['log_level'] if not DEBUG_LOGGING else logging.DEBUG)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # configure logger default
    logging.basicConfig(
        level=logging.DEBUG,
        format=logging_settings['logging_format'],
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            file_handler,
            rich_handler,
        ]
    )

init_logging()

from . import cli

if DEBUG:
    sys.setrecursionlimit(300)


if main_settings['modify_gc']:
    """
    At the start I modify the garbage collector to run a bit fewer times.
    This should increase speed:
    https://mkennedy.codes/posts/python-gc-settings-change-this-and-make-your-app-go-20pc-faster/
    """
    # Clean up what might be garbage so far.
    gc.collect(2)

    allocs, gen1, gen2 = gc.get_threshold()
    allocs = 50_000  # Start the GC sequence every 50K not 700 allocations.
    gen1 = gen1 * 2
    gen2 = gen2 * 2
    gc.set_threshold(allocs, gen1, gen2)


