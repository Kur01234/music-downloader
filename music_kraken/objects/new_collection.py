from __future__ import annotations

from collections import defaultdict
from typing import TypeVar, Generic, Dict, Optional, Iterable, List
from .parents import OuterProxy

T = TypeVar('T', bound=OuterProxy)


class Collection(Generic[T]):
    _data: List[T]

    _indexed_values: Dict[str, set]
    _indexed_to_objects: Dict[any, list]

    shallow_list = property(fget=lambda self: self.data)

    def __init__(
            self,
            data: Optional[Iterable[T]] = None,
            sync_on_append: Dict[str, "Collection"] = None,
            contain_given_in_attribute: Dict[str, "Collection"] = None,
            contain_attribute_in_given: Dict[str, "Collection"] = None,
            append_object_to_attribute: Dict[str, T] = None
    ) -> None:
        self._contains_ids = set()
        self._data = []
        self.upper_collections: List[Collection[T]] = []
        self.contained_collections: List[Collection[T]] = []

        # List of collection attributes that should be modified on append
        # Key: collection attribute (str) of appended element
        # Value: main collection to sync to
        self.sync_on_append: Dict[str, Collection] = sync_on_append or {}
        self.contain_given_in_attribute: Dict[str, Collection] = contain_given_in_attribute or {}
        self.contain_attribute_in_given: Dict[str, Collection] = contain_attribute_in_given or {}
        self.append_object_to_attribute: Dict[str, T] = append_object_to_attribute or {}

        self.contain_self_on_append: List[str] = []

        self._indexed_values = defaultdict(set)
        self._indexed_to_objects = defaultdict(list)

        self.extend(data)

    def _map_element(self, __object: T, from_map: bool = False):
        self._contains_ids.add(__object.id)

        for name, value in __object.indexing_values:
            if value is None:
                continue

            self._indexed_values[name].add(value)
            self._indexed_to_objects[value].append(__object)

        if not from_map:
            for attribute, new_object in self.contain_given_in_attribute.items():
                __object.__getattribute__(attribute).contain_collection_inside(new_object)

            for attribute, new_object in self.contain_given_in_attribute.items():
                new_object.contain_collection_inside(__object.__getattribute__(attribute))

            for attribute, new_object in self.append_object_to_attribute.items():
                __object.__getattribute__(attribute).append(new_object, from_map=True)

    def _unmap_element(self, __object: T):
        self._contains_ids.remove(__object.id)

        for name, value in __object.indexing_values:
            if value is None:
                continue
            if value not in self._indexed_values[name]:
                continue

            try:
                self._indexed_to_objects[value].remove(__object)
            except ValueError:
                continue

            if not len(self._indexed_to_objects[value]):
                self._indexed_values[name].remove(value)

    def _contained_in_self(self, __object: T) -> bool:
        if __object.id in self._contains_ids:
            return True

        for name, value in __object.indexing_values:
            if value is None:
                continue
            if value in self._indexed_values[name]:
                return True
        return False

    def _get_root_collections(self) -> List["Collection"]:
        if not len(self.upper_collections):
            return [self]

        root_collections = []
        for upper_collection in self.upper_collections:
            root_collections.extend(upper_collection._get_root_collections())
        return root_collections

    @property
    def _is_root(self) -> bool:
        return len(self.upper_collections) <= 0

    def _contained_in_sub(self, __object: T, break_at_first: bool = True) -> List["Collection"]:
        results = []

        if self._contained_in_self(__object):
            return [self]

        for collection in self.contained_collections:
            results.extend(collection._contained_in_sub(__object, break_at_first=break_at_first))
            if break_at_first:
                return results

        return results

    def _get_parents_of_multiple_contained_children(self, __object: T):
        results = []
        if len(self.contained_collections) < 2 or self._contained_in_self(__object):
            return results

        count = 0

        for collection in self.contained_collections:
            sub_results = collection._get_parents_of_multiple_contained_children(__object)

            if len(sub_results) > 0:
                count += 1
                results.extend(sub_results)

        if count >= 2:
            results.append(self)

        return results

    def _merge_in_self(self, __object: T, from_map: bool = False):
        """
        1. find existing objects
        2. merge into existing object
        3. remap existing object
        """
        if __object.id in self._contains_ids:
            return

        existing_object: DatabaseObject = None

        for name, value in __object.indexing_values:
            if value is None:
                continue
            if value in self._indexed_values[name]:
                existing_object = self._indexed_to_objects[value][0]
                if existing_object.id == __object.id:
                    return None

                break

        if existing_object is None:
            return None

        existing_object.merge(__object, replace_all_refs=True)

        # just a check if it really worked
        if existing_object.id != __object.id:
            raise ValueError("This should NEVER happen. Merging doesn't work.")

        self._map_element(existing_object, from_map=from_map)

    def contains(self, __object: T) -> bool:
        return len(self._contained_in_sub(__object)) > 0

    def _append(self, __object: T, from_map: bool = False):
        for attribute, to_sync_with in self.sync_on_append.items():
            pass
            to_sync_with.sync_with_other_collection(__object.__getattribute__(attribute))

        self._map_element(__object, from_map=from_map)
        self._data.append(__object)

    def append(self, __object: Optional[T], already_is_parent: bool = False, from_map: bool = False):
        if __object is None:
            return
        if __object.id in self._contains_ids:
            return

        exists_in_collection = self._contained_in_sub(__object)
        if len(exists_in_collection) and self is exists_in_collection[0]:
            # assuming that the object already is contained in the correct collections
            if not already_is_parent:
                self._merge_in_self(__object, from_map=from_map)
            return

        if not len(exists_in_collection):
            self._append(__object, from_map=from_map)
        else:
            pass
            exists_in_collection[0]._merge_in_self(__object, from_map=from_map)

        if not already_is_parent or not self._is_root:
            for parent_collection in self._get_parents_of_multiple_contained_children(__object):
                pass
                parent_collection.append(__object, already_is_parent=True, from_map=from_map)

    def extend(self, __iterable: Optional[Iterable[T]]):
        if __iterable is None:
            return

        for __object in __iterable:
            self.append(__object)

    def sync_with_other_collection(self, equal_collection: "Collection"):
        """
        If two collections always need to have the same values, this can be used.

        Internally:
        1. import the data from other to self
            - _data
            - contained_collections
        2. replace all refs from the other object, with refs from this object
        """
        if equal_collection is self:
            return

        # don't add the elements from the subelements from the other collection.
        # this will be done in the next step.
        self.extend(equal_collection._data)
        # add all submodules
        for equal_sub_collection in equal_collection.contained_collections:
            self.contain_collection_inside(equal_sub_collection)

        # now the ugly part
        # replace all refs of the other element with this one
        self._risky_merge(equal_collection)

    def contain_collection_inside(self, sub_collection: "Collection"):
        """
        This collection will ALWAYS contain everything from the passed in collection
        """
        if sub_collection in self.contained_collections:
            return

        self.contained_collections.append(sub_collection)
        sub_collection.upper_collections.append(self)

    @property
    def data(self) -> List[T]:
        return [*self._data,
                *(__object for collection in self.contained_collections for __object in collection.shallow_list)]

    def __len__(self) -> int:
        return len(self._data) + sum(len(collection) for collection in self.contained_collections)

    def __iter__(self) -> Iterator[T]:
        for element in self._data:
            yield element
