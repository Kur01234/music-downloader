from typing import Any, Tuple, Union, List
from pathlib import Path
import logging
from datetime import datetime

import toml

from .attributes.attribute import Attribute, Description, EmptyLine


class ConfigDict(dict):
    def __init__(self, config_reference: "Config", *args, **kwargs):
        self.config_reference: Config = config_reference

        super().__init__(*args, **kwargs)

    def __getitem__(self, __name: str) -> Any:
        return super().__getitem__(__name)
    
    def __setitem__(self, __key: Any, __value: Any, from_attribute: bool = False, is_parsed: bool = False) -> None:
        if not from_attribute:
            attribute: Attribute = self.config_reference.attribute_map[__key]
            if is_parsed:
                attribute.value = __value
            else:
                attribute.parse(__value)
            self.config_reference.write()

            __value = attribute.value

        return super().__setitem__(__key, __value)


class Config:
    def __init__(self, component_list: Tuple[Union[Attribute, Description, EmptyLine], ...], config_file: Path) -> None:
        self.config_file: Path = config_file

        self.component_list: List[Union[Attribute, Description, EmptyLine]] = [
            Description(f"""IMPORTANT: If you modify this file, the changes for the actual setting, will be kept as is.
The changes you make to the comments, will be discarded, next time you run music-kraken. Have fun!

Latest reset: {datetime.now()}

   _____              
  / ____|              
 | |  __   __ _  _   _ 
 | | |_ | / _` || | | |
 | |__| || (_| || |_| |
  \_____| \__,_| \__, |
                  __/ |
                 |___/ 
""")]

        self.component_list.extend(component_list)
        self.loaded_settings: ConfigDict = ConfigDict(self)

        self.attribute_map = {}
        for component in self.component_list:
            if not isinstance(component, Attribute):
                continue
            
            component.initialize_from_config(self.loaded_settings)
            self.attribute_map[component.name] = component

    @property
    def toml_string(self):
        return "\n".join(component.toml_string for component in self.component_list)

    def write(self):
        print(self.config_file)
        with self.config_file.open("w", encoding="utf-8") as conf_file:
            conf_file.write(self.toml_string)

    def read(self):
        if not self.config_file.is_file():
            logging.info(f"Config file at '{self.config_file}' doesn't exist => generating")
            self.write()
            return
        
        toml_data = {}
        with self.config_file.open("r", encoding="utf-8") as conf_file:
            toml_data = toml.load(conf_file)

        for component in self.component_list:
            if isinstance(component, Attribute):
                component.load_toml(toml_data)
