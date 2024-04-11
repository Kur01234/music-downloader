from __future__ import annotations

from typing import List, Optional, Dict, Tuple, Type, Union, TypedDict

from .collection import Collection
from .metadata import (
    Mapping as id3Mapping,
    ID3Timestamp,
    Metadata
)
from ..utils.string_processing import unify, hash_url

from .parents import OuterProxy as Base

from ..utils.config import main_settings


class ArtworkVariant(TypedDict):
    url: str
    width: int
    height: int
    deviation: float


class Artwork:
    def __init__(self, *variants: List[ArtworkVariant]) -> None:
        self._variant_mapping: Dict[str, ArtworkVariant] = {}

        for variant in variants:
            self.append(**variant)

    @staticmethod
    def _calculate_deviation(*dimensions: List[int]) -> float:
        return sum(abs(d - main_settings["preferred_artwork_resolution"]) for d in dimensions) / len(dimensions)

    def append(self, url: str, width: int = main_settings["preferred_artwork_resolution"], height: int = main_settings["preferred_artwork_resolution"], **kwargs) -> None:
        if url is None:
            return
        
        self._variant_mapping[hash_url(url=url)] = {
            "url": url,
            "width": width,
            "height": height,
            "deviation": self._calculate_deviation(width, height),
        }

    @property
    def best_variant(self) -> ArtworkVariant:
        if len(self._variant_mapping.keys()) <= 0:
            return None
        return min(self._variant_mapping.values(), key=lambda x: x["deviation"])

    def __merge__(self, other: Artwork, override: bool = False) -> None:
        for key, value in other._variant_mapping.items():
            if key not in self._variant_mapping or override:
                self._variant_mapping[key] = value

    def __eq__(self, other: Artwork) -> bool:
        return any(a == b for a, b in zip(self._variant_mapping.keys(), other._variant_mapping.keys()))
