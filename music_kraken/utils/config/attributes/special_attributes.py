from pathlib import Path, PosixPath
from typing import Optional, Dict, Set
from urllib.parse import urlparse, urlunparse
import logging

from .attribute import Attribute
from ...exception.config import SettingValueError


class UrlAttribute(Attribute):
    def parse_simple_value(self, value: any) -> any:
        return urlparse(value)
    
    def unparse_simple_value(self, value: any) -> any:
        return urlunparse((value.scheme, value.netloc, value.path, value.params, value.query, value.fragment))


class PathAttribute(Attribute):
    def parse_simple_value(self, value: any) -> Path:
        if isinstance(value, Path) or isinstance(value, PosixPath):
            return value
        return Path(value)
    
    def unparse_simple_value(self, value: Path) -> any:
        return str(value.resolve())



class SelectAttribute(Attribute):
    def __init__(self, name: str, default_value: any, options: tuple, description: Optional[str] = None, ignore_options_for_description = False):
        self.options: tuple = options

        new_description = ""
        if description is not None:
            new_description += description
            new_description += "\n"

        if not ignore_options_for_description:
            new_description += f"{{{', '.join(self.options)}}}"

        super().__init__(name, default_value, description)

    def parse_simple_value(self, value: any) -> any:
        if value in self.options:
            return value
        
        raise SettingValueError(            
            setting_name=self.name,
            setting_value=value,
            rule=f"has to be in the options: {{{', '.join(self.options)}}}."
        )
    
    def unparse_simple_value(self, value: any) -> any:
        return value


class IntegerSelect(Attribute):
    def __init__(self, name: str, default_value: any, options: Dict[int, str], description: Optional[str] = None, ignore_options_for_description = False):
        self.options: Dict[str, int] = options
        self.option_values: Set[int] = set(self.options.values())

        new_description = ""
        if description is not None:
            new_description += description

        description_lines = []

        if description is not None:
            description_lines.append(description)

        description_lines.append("The values can be either an integer or one of the following values:")

        for number, option in self.options.items():
            description_lines.append(f"{number}: {option}")

        super().__init__(name, default_value, "\n".join(description_lines))

    def parse_simple_value(self, value: any) -> any:
        if isinstance(value, str):
            if value not in self.options:
                raise SettingValueError(            
                    setting_name=self.name,
                    setting_value=value,
                    rule=f"has to be in the options: {{{', '.join(self.options.keys())}}}, if it is a string."
                )

            return self.options[value]
        
        return value
    
    def unparse_simple_value(self, value: int) -> any:
        if value in self.option_values:
            for option, v in self.options.items():
                if v == value:
                    return value
        return value


ID3_2_FILE_FORMATS = frozenset((
    "mp3", "mp2", "mp1",    # MPEG-1                ID3.2
    "wav", "wave", "rmi",   # RIFF (including WAV)  ID3.2
    "aiff", "aif", "aifc",  # AIFF                  ID3.2
    "aac", "aacp",          # Raw AAC	            ID3.2
    "tta",                  # True Audio            ID3.2
))
_sorted_id3_2_formats = sorted(ID3_2_FILE_FORMATS)

ID3_1_FILE_FORMATS = frozenset((
    "ape",                  # Monkey's Audio        ID3.1
    "mpc", "mpp", "mp+",    # MusePack              ID3.1
    "wv",                   # WavPack               ID3.1
    "ofr", "ofs"            # OptimFrog             ID3.1
))
_sorted_id3_1_formats = sorted(ID3_1_FILE_FORMATS)


class AudioFormatAttribute(Attribute):
    def __init__(self, name: str, default_value: any, description: Optional[str] = None, ignore_options_for_description = False):
        new_description = ""
        if description is not None:
            new_description += description
            new_description += "\n"

        new_description += f"ID3.2: {{{', '.join(ID3_2_FILE_FORMATS)}}}\n"
        new_description += f"ID3.1: {{{', '.join(ID3_1_FILE_FORMATS)}}}"

        super().__init__(name, default_value, description)

    def parse_simple_value(self, value: any) -> any:
        value = value.strip().lower()
        if value in ID3_2_FILE_FORMATS:
            return value
        if value in ID3_1_FILE_FORMATS:
            logging.debug(f"setting audio format to a format that only supports ID3.1: {v}")
            return value
        
        raise SettingValueError(
            setting_name=self.name,
            setting_value=value,
            rule="has to be a valid audio format, supporting id3 metadata"
        )
    
    def unparse_simple_value(self, value: any) -> any:
        return value

class LoggerAttribute(Attribute):
    def parse_simple_value(self, value: str) -> logging.Logger:
        return logging.getLogger(value)
    
    def unparse_simple_value(self, value: logging.Logger) -> any:
        return value.name
