from ..utils import cli_function

from ...utils.path_manager import LOCATIONS
from ...utils.config import main_settings


def all_paths():
    return {
        "Temp dir": main_settings["temp_directory"],
        "Music dir": main_settings["music_directory"],
        "Conf dir": LOCATIONS.CONFIG_DIRECTORY,
        "Conf file": LOCATIONS.CONFIG_FILE,
        "logging file": main_settings["log_file"],
        "FFMPEG bin": main_settings["ffmpeg_binary"],
        "Cache Dir": main_settings["cache_directory"],
    }


@cli_function
def print_paths():
    for name, path in all_paths().items():
        print(f"{name}:\t{path}")