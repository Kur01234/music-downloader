from typing_extensions import TypeVar
from .option import Options

from .metadata import Metadata, Mapping as ID3Mapping, ID3Timestamp

from .source import Source, SourcePages, SourceTypes

from .song import (
    Song,
    Album,
    Artist,
    Target,
    Lyrics,
    Label
)

from .formatted_text import FormattedText
from .collection import Collection

from .country import Country
from .contact import Contact

from .parents import OuterProxy

from .artwork import Artwork

DatabaseObject = TypeVar('T', bound=OuterProxy)
