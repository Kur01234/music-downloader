from typing import Optional, List, Tuple

from ..utils.enums.contact import ContactMethod
from .parents import OuterProxy


class Contact(OuterProxy):
    COLLECTION_STRING_ATTRIBUTES = tuple()
    SIMPLE_STRING_ATTRIBUTES = {
        "contact_method": None,
        "value": None,
    }

    @property
    def indexing_values(self) -> List[Tuple[str, object]]:
        return [
            ('id', self.id),
            ('value', self.value),
        ]

    def __init__(self, contact_method: ContactMethod, value: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.contact_method: ContactMethod = contact_method
        self.value: str = value

    @classmethod
    def match_url(cls, url: str) -> Optional["Contact"]:
        url = url.strip()

        if url.startswith("mailto:"):
            return cls(ContactMethod.EMAIL, url.replace("mailto:", "", 1))
        
        if url.startswith("tel:"):
            return cls(ContactMethod.PHONE, url.replace("tel:", "", 1))
        
        if url.startswith("fax:"):
            return cls(ContactMethod.FAX, url.replace("fax:", "", 1))

