from typing import Dict, List

import requests


class RotatingObject:
    """
    This will be used for RotatingProxies and invidious instances.
    """
    def __init__(self, object_list: list):
        self._object_list: list = object_list

        if len(self._object_list) <= 0:
            raise ValueError("There needs to be at least one item in a Rotating structure.")

        self._current_index = 0

    @property
    def object(self):
        return self._object_list[self._current_index]

    def __len__(self):
        return len(self._object_list)

    @property
    def next(self):
        self._current_index = (self._current_index + 1) % len(self._object_list)

        return self._object_list[self._current_index]


class RotatingProxy(RotatingObject):
    def __init__(self, proxy_list: List[Dict[str, str]]):
        super().__init__(
            proxy_list if len(proxy_list) > 0 else [None]
        )

    def rotate(self) -> Dict[str, str]:
        return self.next

    @property
    def current_proxy(self) -> Dict[str, str]:
        return super().object
