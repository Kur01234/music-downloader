import weakref
from types import FunctionType
from functools import wraps

from typing import Dict, Set

class Lake:
    def __init__(self):
        self.redirects: Dict[int, int] = {}
        self.id_to_object: Dict[int, object] = {}

    def get_real_object(self, db_object: object) -> object:
        _id = id(db_object)
        while _id in self.redirects:
            _id = self.redirects[_id]

        try:
            return self.id_to_object[_id]
        except KeyError:
            self.add(db_object)
        return db_object

    def add(self, db_object: object):
        self.id_to_object[id(db_object)] = db_object

    def override(self, to_override: object, new_db_object: object):
        _id = id(to_override)
        while _id in self.redirects:
            _id = self.redirects[_id]

        if id(new_db_object) in self.id_to_object:
            print("!!!!!")

        self.add(new_db_object)
        self.redirects[_id] = id(new_db_object)
        # if _id in self.id_to_object:
        # del self.id_to_object[_id]

    def is_same(self, __object: object, other: object) -> bool:
        _self_id = id(__object)
        while _self_id in self.redirects:
            _self_id = self.redirects[_self_id]

        _other_id = id(other)
        while _other_id in self.redirects:
            _other_id = self.redirects[_other_id]

        return _self_id == _other_id


lake = Lake()


def wrapper(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        return method(*(lake.get_real_object(args[0]), *args[1:]), **kwargs)

    return wrapped


class BaseClass:
    def __new__(cls, *args, **kwargs):
        instance = cls(*args, **kwargs)
        print("new")
        lake.add(instance)
        return instance

    def __eq__(self, other):
        return lake.is_same(self, other)

    def _risky_merge(self, to_replace):
        lake.override(to_replace, self)


class MetaClass(type):
    def __new__(meta, classname, bases, classDict):
        bases = (*bases, BaseClass)
        newClassDict = {}

        ignore_functions: Set[str] = {"__new__", "__init__"}

        for attributeName, attribute in classDict.items():
            if isinstance(attribute, FunctionType) and (attributeName not in ignore_functions):
                """
                The funktion new and init shouldn't be accounted for because we can assume the class is 
                independent on initialization.
                """
                attribute = wrapper(attribute)

            newClassDict[attributeName] = attribute

        print()

        for key, value in object.__dict__.items():
            # hasattr( value, '__call__' ) and
            if hasattr(value, '__call__') and value not in newClassDict and key not in ("__new__", "__init__"):
                newClassDict[key] = wrapper(value)

        new_instance = type.__new__(meta, classname, bases, newClassDict)

        lake.add(new_instance)

        return new_instance
