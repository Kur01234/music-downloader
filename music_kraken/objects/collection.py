from __future__ import annotations

from collections import defaultdict
from typing import TypeVar, Generic, Dict, Optional, Iterable, List, Iterator, Tuple, Generator, Union, Any, Set
import copy

from .parents import OuterProxy
from ..utils import object_trace
from ..utils import output, BColors

T = TypeVar('T', bound=OuterProxy)


class Collection(Generic[T]):
    __is_collection__ = True

    _data: List[T]

    _indexed_from_id: Dict[int, Dict[str, Any]]
    _indexed_values: Dict[str, Dict[Any, T]]

    shallow_list = property(fget=lambda self: self.data)

    def __init__(
            self,
            data: Optional[Iterable[T]] = None,
            sync_on_append: Dict[str, Collection] = None,
            append_object_to_attribute: Dict[str, T] = None,
            extend_object_to_attribute: Dict[str, Collection] = None,
    ) -> None:
        self._collection_for: dict = dict()

        self._contains_ids = set()
        self._data = []

        # List of collection attributes that should be modified on append
        # Key: collection attribute (str) of appended element
        # Value: main collection to sync to
        self.append_object_to_attribute: Dict[str, T] = append_object_to_attribute or {}
        self.extend_object_to_attribute: Dict[str, Collection[T]] = extend_object_to_attribute or {}
        self.sync_on_append: Dict[str, Collection] = sync_on_append or {}
        self.pull_from: List[Collection] = []
        self.push_to: List[Collection] = []

        # This is to cleanly unmap previously mapped items by their id
        self._indexed_from_id: Dict[int, Dict[str, Any]] = defaultdict(dict)
        # this is to keep track and look up the actual objects
        self._indexed_values: Dict[str, Dict[Any, T]] = defaultdict(dict)

        self.extend(data)

    def __hash__(self) -> int:
        return id(self)

    @property
    def collection_names(self) -> List[str]:
        return list(set(self._collection_for.values()))

    def __repr__(self) -> str:
        return f"Collection({' | '.join(self.collection_names)} {id(self)})"

    def _map_element(self, __object: T, no_unmap: bool = False, **kwargs):
        if not no_unmap:
            self._unmap_element(__object.id)

        self._indexed_from_id[__object.id]["id"] = __object.id
        self._indexed_values["id"][__object.id] = __object

        for name, value in __object.indexing_values:
            if value is None or value == __object._inner._default_values.get(name):
                continue

            self._indexed_values[name][value] = __object
            self._indexed_from_id[__object.id][name] = value

    def _unmap_element(self, __object: Union[T, int]):
        obj_id = __object.id if isinstance(__object, OuterProxy) else __object

        if obj_id not in self._indexed_from_id:
            return

        for name, value in self._indexed_from_id[obj_id].items():
            if value in self._indexed_values[name]:
                del self._indexed_values[name][value]

        del self._indexed_from_id[obj_id]

    def _remap(self):
        # reinitialize the mapping to clean it without time consuming operations
        self._indexed_from_id: Dict[int, Dict[str, Any]] = defaultdict(dict)
        self._indexed_values: Dict[str, Dict[Any, T]] = defaultdict(dict)

        for e in self._data:
            self._map_element(e, no_unmap=True)


    def _find_object(self, __object: T, **kwargs) -> Optional[T]:
        self._remap()

        if __object.id in self._indexed_from_id:
            return self._indexed_values["id"][__object.id]

        for name, value in __object.indexing_values:
            if value in self._indexed_values[name]:
                return self._indexed_values[name][value]

        return None
    
    def _append_new_object(self, other: T, **kwargs):
        """
        This function appends the other object to the current collection.
        This only works if not another object, which represents the same real life object exists in the collection.
        """
        
        self._data.append(other)
        other._inner._is_in_collection.add(self)

        for attribute, a in self.sync_on_append.items():
            # syncing two collections by reference
            b = other.__getattribute__(attribute)
            if a is b:
                continue

            object_trace(f"Syncing [{a}] = [{b}]")

            b_data = b.data.copy()
            b_collection_for = b._collection_for.copy()

            del b

            for synced_with, key in b_collection_for.items():
                synced_with.__setattr__(key, a)
                a._collection_for[synced_with] = key

            a.extend(b_data, **kwargs)

        # all of the existing hooks to get the defined datastructures
        for collection_attribute, generator in self.extend_object_to_attribute.items():
            other.__getattribute__(collection_attribute).extend(generator, **kwargs)

        for attribute, new_object in self.append_object_to_attribute.items():
            other.__getattribute__(attribute).append(new_object, **kwargs)

    def append(self, other: Optional[T], **kwargs):
        """
        If an object, that represents the same entity exists in a relevant collection,
        merge into this object. (and remap)
        Else append to this collection.

        :param other:
        :return:
        """

        if other is None:
            return
        if not other._inner._has_data:
            return
        if other.id in self._indexed_from_id:
            return

        object_trace(f"Appending {other.option_string} to {self}")


        # switching collection in the case of push to
        for c in self.push_to:
            r = c._find_object(other)
            if r is not None:
                # output("found push to", r, other, c, self, color=BColors.RED, sep="\t")
                return c.append(other, **kwargs)

        for c in self.pull_from:
            r = c._find_object(other)
            if r is not None:
                # output("found pull from", r, other, c, self, color=BColors.RED, sep="\t")
                c.remove(r, existing=r, **kwargs)
        
        existing = self._find_object(other)

        if existing is None:
            self._append_new_object(other, **kwargs)
        else:
            existing.merge(other, **kwargs)

    def remove(self, *other_list: List[T], silent: bool = False, existing: Optional[T] = None, remove_from_other_collection=True, **kwargs):
        other: T
        for other in other_list:
            existing: Optional[T] = existing or self._indexed_values["id"].get(other.id, None)
            if existing is None:
                if not silent:
                    raise ValueError(f"Object {other} not found in {self}")
                return other

            if remove_from_other_collection:
                for c in copy.copy(other._inner._is_in_collection):
                    c.remove(other, silent=True, remove_from_other_collection=False, **kwargs)
                other._inner._is_in_collection = set()
            else:
                self._data.remove(existing)
                self._unmap_element(existing)

    def contains(self, __object: T) -> bool:
        return self._find_object(__object) is not None

    def extend(self, other_collections: Optional[Generator[T, None, None]], **kwargs):
        if other_collections is None:
            return

        for other_object in other_collections:
            self.append(other_object, **kwargs)

    @property
    def data(self) -> List[T]:
        return list(self.__iter__())

    def __len__(self) -> int:
        return len(self._data)

    @property
    def empty(self) -> bool:
        return self.__len__() <= 0

    def __iter__(self) -> Iterator[T]:
        yield from self._data

    def __merge__(self, other: Collection, **kwargs):
        object_trace(f"merging {str(self)} | {str(other)}")
        self.extend(other, **kwargs)

    def __getitem__(self, item: int):
        return self._data[item]

    def get(self, item: int, default = None):
        if item >= len(self._data):
            return default
        return self._data[item]

    def __eq__(self, other: Collection) -> bool:
        if self.empty and other.empty:
            return True
        
        return self._data == other._data
