from typing import Tuple

from .config import Config
from .config_files import (
    main_config,
    logging_config,
    youtube_config,
)

_sections: Tuple[Config, ...] = (
    main_config.config,
    logging_config.config,
    youtube_config.config
)

def read_config():
    for section in _sections:
        section.read()

    # special cases
    if main_settings['tor']:
        main_settings['proxies'] = {
            'http': f'socks5h://127.0.0.1:{main_settings["tor_port"]}',
            'https': f'socks5h://127.0.0.1:{main_settings["tor_port"]}'
        }

def write_config():
    for section in _sections:
        section.write()

main_settings: main_config.SettingsStructure = main_config.config.loaded_settings
logging_settings: logging_config.SettingsStructure = logging_config.config.loaded_settings
youtube_settings: youtube_config.SettingsStructure = youtube_config.config.loaded_settings
