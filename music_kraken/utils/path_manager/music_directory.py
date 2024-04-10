import os
from pathlib import Path
from typing import Optional

from sys import platform
import logging
from os.path import expandvars

import configparser

DEFAULT_MUSIC_DIRECTORY = Path(Path.home(), "Music")


def get_xdg_music_directory() -> Path:
    """
    gets the xdg music directory, for all the linux or bsd folks!
    Thanks to Distant Thunder, as well as Kevin Gruber for making that pull request:
    https://github.com/HeIIow2/music-downloader/pull/6

    XDG_USER_DIRS_FILE reference:
    https://freedesktop.org/wiki/Software/xdg-user-dirs/
    https://web.archive.org/web/20230322012953/https://freedesktop.org/wiki/Software/xdg-user-dirs/
    """

    xdg_user_dirs_file = Path(os.environ.get("XDG_CONFIG_HOME") or Path(Path.home(), ".config"), "user-dirs.dirs")
    xdg_user_dirs_default_file = Path("/etc/xdg/user-dirs.defaults")

    def get_music_dir_from_xdg_file(xdg_file_path: os.PathLike) -> Optional[Path]:
        try:
            with open(xdg_file_path, 'r', encoding="utf-8") as f:
                data = "[XDG_USER_DIRS]\n" + f.read()
            config = configparser.ConfigParser(allow_no_value=True)
            config.read_string(data)
            xdg_config = config['XDG_USER_DIRS']
            return Path(expandvars(xdg_config['xdg_music_dir'].strip('"')))

        except (FileNotFoundError, KeyError) as e:
            logging.warning(
                f"Missing file or No entry found for \"xdg_music_dir\" in: \"{xdg_file_path}\".\n"
            )
            logging.debug(str(e))

    music_dir = get_music_dir_from_xdg_file(xdg_user_dirs_file)
    if music_dir is not None:
        return music_dir
    music_dir = get_music_dir_from_xdg_file(xdg_user_dirs_default_file)
    if music_dir is not None:
        return music_dir

    logging.warning(f"couldn't find a XDG music dir, falling back to: {DEFAULT_MUSIC_DIRECTORY}")
    return DEFAULT_MUSIC_DIRECTORY


def get_music_directory() -> Path:
    if platform != "linux":
        return DEFAULT_MUSIC_DIRECTORY

    return get_xdg_music_directory()
