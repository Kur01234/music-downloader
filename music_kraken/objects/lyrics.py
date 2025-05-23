from typing import List
from collections import defaultdict
import pycountry

from .parents import OuterProxy
from .source import Source, SourceCollection
from .formatted_text import FormattedText
from .country import Language
from .metadata import (
    Mapping as id3Mapping,
    ID3Timestamp,
    Metadata
)


class Lyrics(OuterProxy):
    text: FormattedText
    language: Language

    source_collection: SourceCollection

    _default_factories = {
        "text": FormattedText,
        "language": lambda: Language.by_alpha_2("en"),

        "source_collection": SourceCollection,
    }

    # This is automatically generated
    def __init__(self, text: FormattedText = None, language: Language = None, source_list: SourceCollection = None,
                 **kwargs) -> None:
        super().__init__(text=text, language=language, source_list=source_list, **kwargs)

    @property
    def metadata(self) -> Metadata:
        return Metadata({
            id3Mapping.UNSYNCED_LYRICS: [self.text.plaintext]
        })

