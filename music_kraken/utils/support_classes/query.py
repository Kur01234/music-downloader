from typing import Optional, List

from ...objects import Artist, Album, Song, DatabaseObject

class Query:
    def __init__(
        self,
        raw_query: str = "",
        music_object: DatabaseObject = None
    ) -> None:
        self.raw_query: str = raw_query
        self.music_object: Optional[DatabaseObject] = music_object
        
    @property
    def is_raw(self) -> bool:
        return self.music_object is None

    @property
    def default_search(self) -> List[str]:
        if self.music_object is None:
            return [self.raw_query]
        
        if isinstance(self.music_object, Artist):
            return [self.music_object.name]
        
        if isinstance(self.music_object, Song):
            return [f"{artist.name} - {self.music_object}" for artist in self.music_object.main_artist_collection]
        
        if isinstance(self.music_object, Album):
            return [f"{artist.name} - {self.music_object}" for artist in self.music_object.artist_collection]
        
        return [self.raw_query]
