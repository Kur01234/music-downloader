from typing import TypedDict, List
from urllib.parse import ParseResult
from logging import Logger
from pathlib import Path
import logging

from ...path_manager import LOCATIONS
from ..config import Config
from ..attributes.attribute import Attribute, EmptyLine
from ..attributes.special_attributes import (
    IntegerSelect,
    LoggerAttribute
)


config = Config([
    Attribute(name="logging_format", default_value="%(levelname)s:%(name)s:%(message)s", description="""Logging settings for the actual logging:
Reference for the logging formats: https://docs.python.org/3/library/logging.html#logrecord-attributes"""),
    IntegerSelect(
        name="log_level",
        default_value=logging.INFO,
        options={
            "CRITICAL": 50,
            "ERROR": 40,
            "WARNING": 30,
            "INFO": 20,
            "DEBUG": 10,
            "NOTSET": 0
        }
    ),

    LoggerAttribute(
        name="download_logger",
        description="The logger for downloading.",
        default_value="download"
    ),
    LoggerAttribute(
        name="tagging_logger",
        description="The logger for tagging id3 containers.",
        default_value="tagging"
    ),
    LoggerAttribute(
        name="codex_logger",
        description="The logger for streaming the audio into an uniform codex.",
        default_value="codex"
    ),
    LoggerAttribute(
        name="object_logger",
        description="The logger for creating Data-Objects.",
        default_value="object"
    ),
    LoggerAttribute(
        name="database_logger",
        description="The logger for Database operations.",
        default_value="database"
    ),
    LoggerAttribute(
        name="musify_logger",
        description="The logger for the musify scraper.",
        default_value="musify"
    ),
    LoggerAttribute(
        name="youtube_logger",
        description="The logger for the youtube scraper.",
        default_value="youtube"
    ),
    LoggerAttribute(
        name="youtube_music_logger",
        description="The logger for the youtube music scraper.\n(The scraper is seperate to the youtube scraper)",
        default_value="youtube_music"
    ),
    LoggerAttribute(
        name="metal_archives_logger",
        description="The logger for the metal archives scraper.",
        default_value="metal_archives"
    ),
    LoggerAttribute(
        name="genius_logger",
        description="The logger for the genius scraper",
        default_value="genius"
    ),
    LoggerAttribute(
        name="bandcamp_logger",
        description="The logger for the bandcamp scraper",
        default_value="bandcamp"
    )

], LOCATIONS.get_config_file("logging"))


class SettingsStructure(TypedDict):
    # logging
    logging_format: str
    log_level: int
    download_logger: Logger
    tagging_logger: Logger
    codex_logger: Logger
    object_logger: Logger
    database_logger: Logger
    musify_logger: Logger
    youtube_logger: Logger
    youtube_music_logger: Logger
    metal_archives_logger: Logger
    genius_logger: Logger
    bandcamp_logger: Logger