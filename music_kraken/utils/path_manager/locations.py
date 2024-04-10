import configparser
from pathlib import Path
import os
from os.path import expandvars
import logging
from sys import platform

import tempfile
from typing import Optional

from pyffmpeg import FFmpeg


from .music_directory import get_music_directory
from .config_directory import get_config_directory


class Locations:
    @staticmethod
    def _get_env(key: str, default: Path, default_for_windows: bool = True) -> Optional[Path]:
        res = os.environ.get(key.upper())
        if res is not None:
            return res

        xdg_user_dirs_file = os.environ.get("XDG_CONFIG_HOME") or Path(Path.home(), ".config", "user-dirs.dirs")
        xdg_user_dirs_default_file = Path("/etc/xdg/user-dirs.defaults")

        def get_dir_from_xdg_file(xdg_file_path: os.PathLike) -> Optional[Path]:
            nonlocal key

            try:
                with open(xdg_file_path, 'r') as f:
                    data = "[XDG_USER_DIRS]\n" + f.read()
                config = configparser.ConfigParser(allow_no_value=True)
                config.read_string(data)
                xdg_config = config['XDG_USER_DIRS']

                return Path(expandvars(xdg_config[key.lower()].strip('"')))

            except (FileNotFoundError, KeyError) as e:
                logging.warning(
                    f"Missing file or No entry found for \"{key}\" in: \"{xdg_file_path}\".\n"
                )
                logging.debug(str(e))

        res = get_dir_from_xdg_file(xdg_user_dirs_file)
        if res is not None:
            return res

        res = get_dir_from_xdg_file(xdg_user_dirs_default_file)
        if res is not None:
            return res

        logging.warning(f"couldn't find a {key}, falling back to: {default}")

        if not default_for_windows and platform == "linux":
            return

        return default

    def __init__(self, application_name: os.PathLike = "music-kraken"):
        self.FILE_ENCODING: str = "utf-8"
        
        self.TEMP_DIRECTORY = Path(tempfile.gettempdir(), application_name)
        self.TEMP_DIRECTORY.mkdir(exist_ok=True, parents=True)

        self.MUSIC_DIRECTORY = get_music_directory()

        self.CONFIG_DIRECTORY = get_config_directory(str(application_name))
        self.CONFIG_DIRECTORY.mkdir(exist_ok=True, parents=True)
        self.CONFIG_FILE = Path(self.CONFIG_DIRECTORY, f"{application_name}.conf")
        self.LEGACY_CONFIG_FILE = Path(self.CONFIG_DIRECTORY, f"{application_name}.conf")

        self.CACHE_DIRECTORY = self._get_env("XDG_CACHE_HOME", Path(Path.home(), ".cache"))
        if self.CACHE_DIRECTORY is None:
            logging.warning(f"Could not find a cache dir. Falling back to the temp dir: {self.TEMP_DIRECTORY}")
            self.CACHE_DIRECTORY = self.TEMP_DIRECTORY
        else:
            self.CACHE_DIRECTORY = Path(self.CACHE_DIRECTORY, application_name)
        self.CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        
        self.FFMPEG_BIN = Path(FFmpeg(enable_log=False).get_ffmpeg_bin())

    def get_config_file(self, config_name: str) -> Path:
        return Path(self.CONFIG_DIRECTORY, f"{config_name}.toml")

    def get_log_file(self, file_name: os.PathLike) -> Path:
        return Path(self.TEMP_DIRECTORY, file_name)
