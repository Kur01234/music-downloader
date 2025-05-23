from __future__ import annotations

import random
from collections import defaultdict
from functools import lru_cache
from typing import Optional, Dict, Tuple, List, Type, Generic, Any, TypeVar, Set

from pathlib import Path
import inspect

from .source import SourceCollection
from .metadata import Metadata
from ..utils import get_unix_time, object_trace, generate_id
from ..utils.config import logging_settings, main_settings
from ..utils.shared import HIGHEST_ID, DEBUG_PRINT_ID
from ..utils.hacking import MetaClass

LOGGER = logging_settings["object_logger"]

P = TypeVar("P", bound="OuterProxy")


class InnerData:
    """
    This is the core class, which is used for every Data class.
    The attributes are set, and can be merged.

    The concept is, that the outer class proxies this class.
    If the data in the wrapper class has to be merged, then this class is just replaced and garbage collected.
    """

    _refers_to_instances: set = None
    _is_in_collection: set = None

    _has_data: bool = False
    """
    Attribute versions keep track, of if the attribute has been changed.
    """

    def __init__(self, object_type, **kwargs):
        self._refers_to_instances = set()
        self._is_in_collection = set()

        self._fetched_from: dict = {}

        # initialize the default values
        self._default_values = {}
        for name, factory in object_type._default_factories.items():
            self._default_values[name] = factory()

        for key, value in kwargs.items():
            if hasattr(value, "__is_collection__"):
                value._collection_for[self] = key
            
            self.__setattr__(key, value)

            if self._has_data:
                continue
    
    def __setattr__(self, key: str, value):
        if self._has_data or not hasattr(self, "_default_values"):
            return super().__setattr__(key, value)
        
        super().__setattr__("_has_data", not (key in self._default_values and self._default_values[key] == value))
        return super().__setattr__(key, value)

    def __hash__(self):
        return self.id

    def __merge__(self, __other: InnerData, **kwargs):
        """
        :param __other:
        :return:
        """

        self._fetched_from.update(__other._fetched_from)
        self._is_in_collection.update(__other._is_in_collection)

        for key, value in __other.__dict__.copy().items():
            if key.startswith("_"):
                continue

            if hasattr(value, "__is_collection__") and key in self.__dict__:
                self.__getattribute__(key).__merge__(value, **kwargs)
                continue

            # just set the other value if self doesn't already have it
            if key not in self.__dict__ or (key in self.__dict__ and self.__dict__[key] == self._default_values.get(key)):
                self.__setattr__(key, value)
                continue

            # if the object of value implemented __merge__, it merges
            existing = self.__getattribute__(key)
            if hasattr(existing, "__merge__"):
                existing.__merge__(value, **kwargs)


class OuterProxy:
    """
    Wraps the inner data, and provides apis, to naturally access those values.
    """

    source_collection: SourceCollection

    _default_factories: dict = {"source_collection": SourceCollection}
    _outer_attribute: Set[str] = {"options", "metadata", "indexing_values", "option_string"}

    DOWNWARDS_COLLECTION_STRING_ATTRIBUTES = tuple()
    UPWARDS_COLLECTION_STRING_ATTRIBUTES = tuple()

    def __init__(self, _id: int = None, dynamic: bool = False, **kwargs):
        _automatic_id: bool = False

        if _id is None:
            """
            generates a random integer id
            the range is defined in the config
            """
            _id = generate_id()
            _automatic_id = True

        kwargs["automatic_id"] = _automatic_id
        kwargs["id"] = _id
        kwargs["dynamic"] = dynamic

        for name, factory in type(self)._default_factories.items():
            if kwargs.get(name, None) is None:
                kwargs[name] = factory()

        collection_data: Dict[str, list] = {}
        for name, value in kwargs.copy().items():
            if isinstance(value, list) and name.endswith("_list"):
                collection_name = name.replace("_list", "_collection")
                collection_data[collection_name] = value

                del kwargs[name]

        self._inner: InnerData = InnerData(type(self), **kwargs)
        self._inner._refers_to_instances.add(self)

        object_trace(f"creating {type(self).__name__} [{self.option_string}]")

        self.__init_collections__()

        for name, data_list in collection_data.items():
            collection = self._inner.__getattribute__(name)
            collection.extend(data_list)

            self._inner.__setattr__(name, collection)

    def __init_collections__(self):
        pass

    def __getattribute__(self, __name: str) -> Any:
        """
        Returns the attribute of _inner if the attribute exists,
        else it returns the attribute of self.

        That the _inner gets checked first is essential for the type hints.
        :param __name:
        :return:
        """

        if __name.startswith("_") or __name in self._outer_attribute or __name.isupper():
            return object.__getattribute__(self, __name)

        _inner: InnerData = super().__getattribute__("_inner")
        try:
            return _inner.__getattribute__(__name)
        except AttributeError:
            return super().__getattribute__(__name)

    def __setattr__(self, __name, __value):
        if not __name.startswith("_") and hasattr(self, "_inner"):
            _inner: InnerData = super().__getattribute__("_inner")
            return _inner.__setattr__(__name, __value)

        return super().__setattr__(__name, __value)

    def _add_other_db_objects(self, object_type: Type[OuterProxy], object_list: List[OuterProxy]):
        pass

    def add_list_of_other_objects(self, object_list: List[OuterProxy]):
        d: Dict[Type[OuterProxy], List[OuterProxy]] = defaultdict(list)

        for db_object in object_list:
            d[type(db_object)].append(db_object)

        for key, value in d.items():
            self._add_other_db_objects(key, value)

    def __hash__(self):
        return id(self)

    def __eq__(self, other: Any):
        return self.__hash__() == other.__hash__()

    def merge(self, __other: Optional[OuterProxy], **kwargs):
        """
        1. merges the data of __other in self
        2. replaces the data of __other with the data of self

        :param __other:
        :return:
        """
        if __other is None:
            return

        a_id = self.id

        a = self
        b = __other

        if a.id == b.id:
            return
        
        # switch instances if more efficient
        if len(b._inner._refers_to_instances) > len(a._inner._refers_to_instances):
            a, b = b, a

        object_trace(f"merging {a.option_string} | {b.option_string}")

        old_inner = b._inner

        for instance in b._inner._refers_to_instances.copy():
            instance._inner = a._inner
            a._inner._refers_to_instances.add(instance)

        a._inner.__merge__(old_inner, **kwargs)
        del old_inner

        self.id = a_id

    def __merge__(self, __other: Optional[OuterProxy], **kwargs):
        self.merge(__other, **kwargs)

    def mark_as_fetched(self, *url_hash_list: List[str]):
        for url_hash in url_hash_list:
            self._inner._fetched_from[url_hash] = {
                "time": get_unix_time(),
                "url": url_hash,
            }

    def already_fetched_from(self, url_hash: str) -> bool:
        res = self._inner._fetched_from.get(url_hash, None)

        if res is None:
            return False

        return get_unix_time() - res["time"] < main_settings["refresh_after"]

    @property
    def metadata(self) -> Metadata:
        """
        This is an interface.
        :return:
        """
        return Metadata()

    @property
    def options(self) -> List[P]:
        r = []

        for collection_string_attribute in self.UPWARDS_COLLECTION_STRING_ATTRIBUTES:
            r.extend(self.__getattribute__(collection_string_attribute))

        r.append(self)

        for collection_string_attribute in self.DOWNWARDS_COLLECTION_STRING_ATTRIBUTES:
            r.extend(self.__getattribute__(collection_string_attribute))

        return r

    @property
    def option_string(self) -> str:
        return self.title_string

    INDEX_DEPENDS_ON: List[str] = []

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        """
        This is an interface.
        It is supposed to return a map of the name and values for all important attributes.
        This helps in comparing classes for equal data (e.g. being the same song but different attributes)

        TODO
        Rewrite this approach into a approach, that is centered around statistics, and not binaries.
        Instead of: one of this matches, it is the same
        This: If enough attributes are similar enough, they are the same

        Returns:
            List[Tuple[str, object]]: the first element in the tuple is the name of the attribute, the second the value.
        """

        return []

    @property
    @lru_cache()
    def all_collections(self):
        r = []

        for key in self._default_factories:
            val = self._inner.__getattribute__(key)
            if hasattr(val, "__is_collection__"):
                r.append(val)

        return r

    @property
    def root_collections(self) -> List[Collection]:
        if len(self.UPWARDS_COLLECTION_STRING_ATTRIBUTES) == 0:
            return [self]

        r = []
        for collection_string_attribute in self.UPWARDS_COLLECTION_STRING_ATTRIBUTES:
            r.extend(self.__getattribute__(collection_string_attribute))

        return r

    def _compile(self, **kwargs):
        pass

    def compile(self, from_root=False, **kwargs):
        # compile from the root
        if not from_root:
            for c in self.root_collections:
                c.compile(from_root=True, **kwargs)
            return

        self._compile(**kwargs)

        for c_attribute in self.DOWNWARDS_COLLECTION_STRING_ATTRIBUTES:
            for c in self.__getattribute__(c_attribute):
                c.compile(from_root=True, **kwargs)

    TITEL = "id"
    @property
    def title_string(self) -> str:
        return str(self.__getattribute__(self.TITEL)) + (f" {self.id}" if DEBUG_PRINT_ID else "")

    @property
    def title_value(self) -> str:
        return str(self.__getattribute__(self.TITEL))

    def __repr__(self):
        return f"{type(self).__name__}({self.title_string})"

    def get_child_collections(self):
        for collection_string_attribute in self.DOWNWARDS_COLLECTION_STRING_ATTRIBUTES:
            yield self.__getattribute__(collection_string_attribute)

    def get_parent_collections(self):
        for collection_string_attribute in self.UPWARDS_COLLECTION_STRING_ATTRIBUTES:
            yield self.__getattribute__(collection_string_attribute)
