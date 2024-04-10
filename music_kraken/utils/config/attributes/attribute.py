import re
from typing import Optional, List, Union, Iterable, Callable
from dataclasses import dataclass
import logging
import toml
from copy import deepcopy, copy
from urllib.parse import urlparse, urlunparse, ParseResult

from ...exception.config import SettingValueError
from ..utils import comment


LOGGER = logging.getLogger("config")

COMMENT_PREFIX = "#"


def comment_string(uncommented: str) -> str:
    unprocessed_lines = uncommented.split("\n")

    processed_lines: List[str] = []

    for line in unprocessed_lines:
        if line.startswith(COMMENT_PREFIX) or line == "":
            processed_lines.append(line)
            continue

        line = COMMENT_PREFIX + " " + line
        processed_lines.append(line)

    return "\n".join(processed_lines)


@dataclass
class Description:
    description: str

    @property
    def toml_string(self):
        return comment_string(self.description)


class EmptyLine(Description):
    def __init__(self):
        self.description = ""



class Attribute:
    def __init__(
            self,
            name: str,
            default_value: any,
            description: Optional[str] = None,
        ):

        self.name = name

        self.value = self._recursive_parse_object(default_value, self.parse_simple_value)

        self.description: Optional[str] = description
        self.loaded_settings: dict = None

    def initialize_from_config(self, loaded_settings: dict):
        self.loaded_settings = loaded_settings
        self.loaded_settings.__setitem__(self.name, self.value, True)

    def unparse_simple_value(self, value: any) -> any:
        return value

    def parse_simple_value(self, value: any) -> any:
        return value
    
    def _recursive_parse_object(self, __object, callback: Callable):
        __object = copy(__object)

        if isinstance(__object, dict):
            for key, value in __object.items():
                __object[key] = self._recursive_parse_object(value, callback)

            return __object
        
        if isinstance(__object, list) or (isinstance(__object, tuple) and not isinstance(__object, ParseResult)):
            for i, item in enumerate(__object):
                __object[i] = self._recursive_parse_object(item, callback)
            return __object

        return callback(__object)
    
    def parse(self, unparsed_value):
        self.value = self._recursive_parse_object(unparsed_value, self.parse_simple_value)
        return self.value

    def unparse(self, parsed_value):
        return self._recursive_parse_object(parsed_value, self.unparse_simple_value)

    def load_toml(self, loaded_toml: dict) -> bool:
        """
        returns true if succesfull
        """

        if self.name not in loaded_toml:
            LOGGER.warning(f"No setting by the name {self.name} found in the settings file.")
            self.loaded_settings.__setitem__(self.name, self.value, True)
            return

        try:
            self.parse(loaded_toml[self.name])
        except SettingValueError as settings_error:
            logging.warning(settings_error)
            return False
        
        self.loaded_settings.__setitem__(self.name, self.value, True)
        
        return True


    @property
    def toml_string(self) -> str:
        string = ""

        if self.description is not None:
            string += comment(self.description) + "\n"
        
        string += toml.dumps({self.name: self.unparse(self.value)})

        # print(string)
        return string

    def __str__(self):
        return f"{self.description}\n{self.name}={self.value}"

