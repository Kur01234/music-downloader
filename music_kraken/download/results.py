from typing import Tuple, Type, Dict, List, Generator, Union
from dataclasses import dataclass

from ..objects import DatabaseObject
from ..utils.enums.source import SourcePages
from ..pages import Page, EncyclopaediaMetallum, Musify


@dataclass
class Option:
    index: int
    music_object: DatabaseObject


class Results:
    def __init__(self) -> None:
        self._by_index: Dict[int, DatabaseObject] = dict()
        self._page_by_index: Dict[int: Type[Page]] = dict()
        
    def __iter__(self) -> Generator[DatabaseObject, None, None]:
        for option in self.formated_generator():
            if isinstance(option, Option):
                yield option.music_object
    
    def formated_generator(self, max_items_per_page: int = 10) -> Generator[Union[Type[Page], Option], None, None]:
        self._by_index = dict()
        self._page_by_index = dict()
    
    def get_music_object_by_index(self, index: int) -> Tuple[Type[Page], DatabaseObject]:
        # if this throws a key error, either the formatted generator needs to be iterated, or the option doesn't exist.
        return self._page_by_index[index], self._by_index[index]


class SearchResults(Results):
    def __init__(
        self,
        pages: Tuple[Type[Page], ...] = None
        
    ) -> None:
        super().__init__()
        
        self.pages = pages or []
        # this would initialize a list for every page, which I don't think I want
        # self.results = Dict[Type[Page], List[DatabaseObject]] = {page: [] for page in self.pages}
        self.results: Dict[Type[Page], List[DatabaseObject]] = {}
        
    def add(self, page: Type[Page], search_result: List[DatabaseObject]):
        """
        adds a list of found music objects to the according page
        WARNING: if a page already has search results, they are just gonna be overwritten
        """
        
        self.results[page] = search_result

    def get_page_results(self, page: Type[Page]) -> "PageResults":
        return PageResults(page, self.results.get(page, []))
    
    def formated_generator(self, max_items_per_page: int = 10):
        super().formated_generator()
        i = 0
        
        for page in self.results:
            yield page
            
            j = 0
            for option in self.results[page]:
                yield Option(i, option)
                self._by_index[i] = option
                self._page_by_index[i] = page
                i += 1
                j += 1
                
                if j >= max_items_per_page:
                    break


class PageResults(Results):
    def __init__(self, page: Type[Page], results: List[DatabaseObject]) -> None:
        super().__init__()
        
        self.page: Type[Page] = page
        self.results: List[DatabaseObject] = results
        
    def formated_generator(self, max_items_per_page: int = 10):
        super().formated_generator()
        i = 0
        
        yield self.page
        
        for option in self.results:
            yield Option(i, option)
            self._by_index[i] = option
            self._page_by_index[i] = self.page
            i += 1
