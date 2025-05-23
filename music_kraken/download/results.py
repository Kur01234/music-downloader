from typing import Tuple, Type, Dict, List, Generator, Union
from dataclasses import dataclass

from ..objects import DatabaseObject
from ..pages import Page, EncyclopaediaMetallum, Musify


@dataclass
class Option:
    index: int
    music_object: DatabaseObject


class Results:
    def __init__(self, max_items_per_page: int = 10, **kwargs) -> None:
        self._by_index: Dict[int, DatabaseObject] = dict()
        self._page_by_index: Dict[int: Type[Page]] = dict()

        self.max_items_per_page = max_items_per_page
        
    def __iter__(self) -> Generator[DatabaseObject, None, None]:
        for option in self.formatted_generator():
            if isinstance(option, Option):
                yield option.music_object
    
    def formatted_generator(self) -> Generator[Union[Type[Page], Option], None, None]:
        self._by_index = dict()
        self._page_by_index = dict()

    def __len__(self) -> int:
        return max(self._by_index.keys())

    def __getitem__(self, index: int): 
        return self._by_index[index]


class SearchResults(Results):
    def __init__(
        self,
        pages: Tuple[Type[Page], ...] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        
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

    def __len__(self) -> int:
        return sum(min(self.max_items_per_page, len(results)) for results in self.results.values())
    
    def formatted_generator(self):
        super().formatted_generator()
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
                
                if j >= self.max_items_per_page:
                    break


class GoToResults(Results):
    def __init__(self, results: List[DatabaseObject], **kwargs):
        self.results: List[DatabaseObject] = results

        super().__init__(**kwargs)

    def __getitem__(self, index: int): 
        return self.results[index]

    def __len__(self) -> int:
        return len(self.results)

    def formatted_generator(self):
        yield from (Option(i, o) for i, o in enumerate(self.results))
    


class PageResults(Results):
    def __init__(self, page: Type[Page], results: List[DatabaseObject], **kwargs) -> None:
        super().__init__(**kwargs)
        
        self.page: Type[Page] = page
        self.results: List[DatabaseObject] = results

        
    def formatted_generator(self, max_items_per_page: int = 10):
        super().formatted_generator()
        i = 0
        
        yield self.page
        
        for option in self.results:
            yield Option(i, option)
            self._by_index[i] = option
            self._page_by_index[i] = self.page
            i += 1

    def __len__(self) -> int:
        return len(self.results)
