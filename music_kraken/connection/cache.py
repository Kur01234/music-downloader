import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
from functools import lru_cache
import logging

from ..utils import output, BColors
from ..utils.config import main_settings
from ..utils.string_processing import fit_to_file_system


@dataclass
class CacheAttribute:
    module: str
    name: str

    created: datetime
    expires: datetime

    additional_info: dict = field(default_factory=dict)

    @property
    def id(self):
        return f"{self.module}_{self.name}"

    @property
    def is_valid(self):
        if isinstance(self.expires, str):
            self.expires = datetime.fromisoformat(self.expires)
        return datetime.now() < self.expires

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


@dataclass
class CacheResult:
    content: bytes
    attribute: CacheAttribute


class Cache:
    def __init__(self, module: str, logger: logging.Logger):
        self.module = module
        self.logger: logging.Logger = logger

        self._dir = main_settings["cache_directory"]
        self.index = Path(self._dir, "index.json")

        if not self.index.is_file():
            with self.index.open("w") as i:
                i.write(json.dumps([]))

        self.cached_attributes: List[CacheAttribute] = []
        self._id_to_attribute = {}

        self._time_fields = {"created", "expires"}
        with self.index.open("r") as i:
            try:
                for c in json.loads(i.read()):
                    for key in self._time_fields:
                        c[key] = datetime.fromisoformat(c[key])

                    ca = CacheAttribute(**c)
                    self.cached_attributes.append(ca)
                    self._id_to_attribute[ca.id] = ca
            except json.JSONDecodeError:
                pass

    @lru_cache()
    def _init_module(self, module: str) -> Path:
        """
        :param module:
        :return: the module path
        """
        r = Path(self._dir, module)
        r.mkdir(exist_ok=True, parents=True)
        return r

    def _write_index(self, indent: int = 4):
        _json = []
        for c in self.cached_attributes:
            d = c.__dict__
            for key in self._time_fields:
                if not isinstance(d[key], str):
                    d[key] = d[key].isoformat()

            _json.append(d)

        with self.index.open("w") as f:
            f.write(json.dumps(_json, indent=indent))

    def _write_attribute(self, cached_attribute: CacheAttribute, write: bool = True) -> bool:
        existing_attribute: Optional[CacheAttribute] = self._id_to_attribute.get(cached_attribute.id)
        if existing_attribute is not None:
            # the attribute exists
            if existing_attribute == cached_attribute:
                return True

            if existing_attribute.is_valid:
                return False

            existing_attribute.__dict__ = cached_attribute.__dict__
        else:
            self.cached_attributes.append(cached_attribute)
            self._id_to_attribute[cached_attribute.id] = cached_attribute

        if write:
            self._write_index()

        return True

    def set(self, content: bytes, name: str, expires_in: float = 10, module: str = "", additional_info: dict = None):
        """
        :param content:
        :param module:
        :param name:
        :param expires_in: the unit is days
        :return:
        """
        if name == "":
            return

        additional_info = additional_info or {}
        module = self.module if module == "" else module

        module_path = self._init_module(module)

        cache_attribute = CacheAttribute(
            module=module,
            name=name,
            created=datetime.now(),
            expires=datetime.now() + timedelta(days=expires_in),
            additional_info=additional_info,
        )
        self._write_attribute(cache_attribute)

        cache_path = fit_to_file_system(Path(module_path, name.replace("/", "_")), hidden_ok=True)
        with cache_path.open("wb") as content_file:
            self.logger.debug(f"writing cache to {cache_path}")
            content_file.write(content)

    def get(self, name: str) -> Optional[CacheResult]:
        path = fit_to_file_system(Path(self._dir, self.module, name.replace("/", "_")), hidden_ok=True)

        if not path.is_file():
            return None

        # check if it is outdated
        if f"{self.module}_{name}" not in self._id_to_attribute:
            path.unlink()
            return
        existing_attribute: CacheAttribute = self._id_to_attribute[f"{self.module}_{name}"]
        if not existing_attribute.is_valid:
            return

        with path.open("rb") as f:
            return CacheResult(content=f.read(), attribute=existing_attribute)

    def clean(self):
        keep = set()

        for ca in self.cached_attributes.copy():
            if ca.name == "":
                continue

            file = fit_to_file_system(Path(self._dir, ca.module, ca.name.replace("/", "_")), hidden_ok=True)

            if not ca.is_valid:
                self.logger.debug(f"deleting cache {ca.id}")
                file.unlink()
                self.cached_attributes.remove(ca)
                del self._id_to_attribute[ca.id]

            else:
                keep.add(file)

        # iterate through every module (folder)
        for module_path in self._dir.iterdir():
            if not module_path.is_dir():
                continue

            # delete all files not in keep
            for path in module_path.iterdir():
                if path not in keep:
                    self.logger.info(f"Deleting cache {path}")
                    path.unlink()

            # delete all empty directories
            for path in module_path.iterdir():
                if path.is_dir() and not list(path.iterdir()):
                    self.logger.debug(f"Deleting cache directory {path}")
                    path.rmdir()

        self._write_index()

    def clear(self):
        """
        delete every file in the cache directory
        :return:
        """

        for path in self._dir.iterdir():
            if path.is_dir():
                for file in path.iterdir():
                    output(f"Deleting file {file}", color=BColors.GREY)
                    file.unlink()
                output(f"Deleting folder {path}", color=BColors.HEADER)
                path.rmdir()
            else:
                output(f"Deleting folder {path}", color=BColors.HEADER)
                path.unlink()

        self.cached_attributes.clear()
        self._id_to_attribute.clear()

        self._write_index()

    def __repr__(self):
        return f"<Cache {self.module}>"
