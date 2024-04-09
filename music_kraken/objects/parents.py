from __future__ import annotations

import random
from collections import defaultdict
from functools import lru_cache

from typing import Optional, Dict, Tuple, List, Type, Generic, Any, TypeVar, Set

from .metadata import Metadata
from ..utils.config import logging_settings
from ..utils.shared import HIGHEST_ID
from ..utils.support_classes.hacking import MetaClass

LOGGER = logging_settings["object_logger"]

P = TypeVar("P", bound="OuterProxy")


class InnerData:
    """
    This is the core class, which is used for every Data class.
    The attributes are set, and can be merged.

    The concept is, that the outer class proxies this class.
    If the data in the wrapper class has to be merged, then this class is just replaced and garbage collected.
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    def __merge__(self, __other: InnerData, override: bool = False):
        """
        TODO
        is default is totally ignored

        :param __other:
        :param override:
        :return:
        """

        for key, value in __other.__dict__.copy().items():
            # just set the other value if self doesn't already have it
            if key not in self.__dict__:
                self.__setattr__(key, value)
                continue

            # if the object of value implemented __merge__, it merges
            existing = self.__getattribute__(key)
            if hasattr(type(existing), "__merge__"):
                existing.__merge__(value, override)
                continue

            # override the existing value if requested
            if override:
                self.__setattr__(key, value)


class OuterProxy:
    """
    Wraps the inner data, and provides apis, to naturally access those values.
    """

    _default_factories: dict = {}
    _outer_attribute: Set[str] = {"options", "metadata", "indexing_values", "option_string"}

    DOWNWARDS_COLLECTION_STRING_ATTRIBUTES = tuple()
    UPWARDS_COLLECTION_STRING_ATTRIBUTES = tuple()

    def __init__(self, _id: int = None, dynamic: bool = False, **kwargs):
        _automatic_id: bool = False

        if _id is None and not dynamic:
            """
            generates a random integer id
            the range is defined in the config
            """
            _id = random.randint(0, HIGHEST_ID)
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

        self._inner: InnerData = InnerData(**kwargs)
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
        """
        :raise: IsDynamicException
        :return:
        """

        if self.dynamic:
            return id(self._inner)

        return self.id

    def __eq__(self, other: Any):
        return self.__hash__() == other.__hash__()

    def merge(self, __other: Optional[OuterProxy], override: bool = False):
        """
        1. merges the data of __other in self
        2. replaces the data of __other with the data of self

        :param __other:
        :param override:
        :return:
        """
        if __other is None:
            _ = "debug"
            return

        self._inner.__merge__(__other._inner, override=override)
        __other._inner = self._inner

    @property
    def metadata(self) -> Metadata:
        """
        This is an interface.
        :return:
        """
        return Metadata()

    @property
    def options(self) -> List[P]:
        return [self]

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

    def __repr__(self):
        return f"{type(self).__name__}({', '.join(key + ': ' + str(val) for key, val in self.indexing_values)})"
