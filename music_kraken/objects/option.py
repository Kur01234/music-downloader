from typing import TYPE_CHECKING, List, Iterable

if TYPE_CHECKING:
    from .parents import DatabaseObject


class Options:
    def __init__(self, option_list: List['DatabaseObject'] = None):
        self._data: List['DatabaseObject'] = option_list or list()

    def __str__(self):
        return "\n".join(f"{i:02d}: {database_object.option_string}" for i, database_object in enumerate(self._data))

    def __iter__(self):
        for database_object in self._data:
            yield database_object
            
    def append(self, element: 'DatabaseObject'):
        self._data.append(element)
        
    def extend(self, iterable: Iterable['DatabaseObject']):
        for element in iterable:
            self.append(element)

    def get_next_options(self, index: int) -> 'Options':
        if index >= len(self._data):
            raise ValueError("Index out of bounds")

        return self._data[index].options

    def __getitem__(self, item: int) -> 'DatabaseObject':
        if type(item) != int:
            raise TypeError("Key needs to be an Integer")
        if item >= len(self._data):
            raise ValueError("Index out of bounds")

        return self._data[item]
    
    def __len__(self) -> int:
        return len(self._data)
