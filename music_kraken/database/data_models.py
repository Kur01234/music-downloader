from typing import List, Union, Type, Optional
from peewee import (
    SqliteDatabase,
    PostgresqlDatabase,
    MySQLDatabase,
    Model,
    CharField,
    IntegerField,
    BooleanField,
    ForeignKeyField,
    TextField
)

"""
**IMPORTANT**:

never delete, modify the datatype or add constrains to ANY existing collumns,
between the versions, that gets pushed out to the users.
Else my function can't update legacy databases, to new databases, 
while keeping the data of the old ones.

EVEN if that means to for example keep decimal values stored in strings.
(not in my codebase though.)
"""


class BaseModel(Model):
    notes: str = CharField(null=True)

    class Meta:
        database = None

    @classmethod
    def Use(cls, database: Union[SqliteDatabase, PostgresqlDatabase, MySQLDatabase]) -> Model:
        cls._meta.database = database
        return cls

    def use(self, database: Union[SqliteDatabase, PostgresqlDatabase, MySQLDatabase]) -> Model:
        self._meta.database = database
        return self

class ObjectModel(BaseModel):
    id: str = CharField(primary_key=True)

class MainModel(BaseModel):
    additional_arguments: str = CharField(null=True)
    notes: str = CharField(null=True)


class Song(MainModel):
    """A class representing a song in the music database."""

    title: str = CharField(null=True)
    isrc: str = CharField(null=True)
    length: int = IntegerField(null=True)
    tracksort: int = IntegerField(null=True)
    genre: str = CharField(null=True)
    

class Album(MainModel):
    """A class representing an album in the music database."""

    title: str = CharField(null=True)
    album_status: str = CharField(null=True)
    album_type: str = CharField(null=True)
    language: str = CharField(null=True)
    date_string: str = CharField(null=True)
    date_format: str = CharField(null=True)
    barcode: str = CharField(null=True)
    albumsort: int = IntegerField(null=True)


class Artist(MainModel):
    """A class representing an artist in the music database."""

    name: str = CharField(null=True)
    country: str = CharField(null=True)
    formed_in_date: str = CharField(null=True)
    formed_in_format: str = CharField(null=True)
    general_genre: str = CharField(null=True)


class Label(MainModel):
    name: str = CharField(null=True)


class Target(ObjectModel):
    """A class representing a target of a song in the music database."""

    file: str = CharField()
    path: str = CharField()
    song = ForeignKeyField(Song, backref='targets')


class Lyrics(ObjectModel):
    """A class representing lyrics of a song in the music database."""

    text: str = TextField()
    language: str = CharField()
    song = ForeignKeyField(Song, backref='lyrics')


class Source(BaseModel):
    """A class representing a source of a song in the music database."""
    ContentTypes = Union[Song, Album, Artist, Lyrics]

    page: str = CharField()
    url: str = CharField()

    content_type: str = CharField()
    content_id: int = CharField()
    # content: ForeignKeyField = ForeignKeyField('self', backref='content_items', null=True)

    @property
    def content_object(self) -> Union[Song, Album, Artist]:
        """Get the content associated with the source as an object."""
        if self.content_type == 'Song':
            return Song.get(Song.id == self.content_id)
        if self.content_type == 'Album':
            return Album.get(Album.id == self.content_id)
        if self.content_type == 'Artist':
            return Artist.get(Artist.id == self.content_id)
        if self.content_type == 'Label':
            return Label.get(Label.id == self.content_id)
        if self.content_type == 'Lyrics':
            return Lyrics.get(Lyrics.id == self.content_id)
        

    @content_object.setter
    def content_object(self, value: Union[Song, Album, Artist]) -> None:
        """Set the content associated with the source as an object."""
        self.content_type = value.__class__.__name__
        self.content_id = value.id


class SongArtist(BaseModel):
    """A class representing the relationship between a song and an artist."""

    song: ForeignKeyField = ForeignKeyField(Song, backref='song_artists')
    artist: ForeignKeyField = ForeignKeyField(Artist, backref='song_artists')
    is_feature: bool = BooleanField(default=False)


class ArtistAlbum(BaseModel):
    """A class representing the relationship between an album and an artist."""

    album: ForeignKeyField = ForeignKeyField(Album, backref='album_artists')
    artist: ForeignKeyField = ForeignKeyField(Artist, backref='album_artists')


class AlbumSong(BaseModel):
    """A class representing the relationship between an album and an song."""
    album: ForeignKeyField = ForeignKeyField(Album, backref='album_artists')
    song: ForeignKeyField = ForeignKeyField(Song, backref='album_artists')


class LabelAlbum(BaseModel):
    label: ForeignKeyField = ForeignKeyField(Label, backref='label_album')
    album: ForeignKeyField = ForeignKeyField(Album, backref='label_album')


class LabelArtist(BaseModel):
    label: ForeignKeyField = ForeignKeyField(Label, backref='label_artist')
    artist: ForeignKeyField = ForeignKeyField(Artist, backref='label_artists')


ALL_MODELS = [
    Song,
    Album,
    Artist,
    Source,
    Lyrics,
    ArtistAlbum,
    Target,
    SongArtist
]

if __name__ == "__main__":
    database_1 = SqliteDatabase(":memory:")
    database_1.create_tables([Song.Use(database_1)])
    database_2 = SqliteDatabase(":memory:")
    database_2.create_tables([Song.Use(database_2)])

    # creating songs, adding it to db_2 if i is even, else to db_1
    for i in range(100):
        song = Song(name=str(i) + "hs")

        db_to_use = database_2 if i % 2 == 0 else database_1
        song.use(db_to_use).save()

    print("database 1")
    for song in Song.Use(database_1).select():
        print(song.name)

    print("database 2")
    for song in Song.Use(database_1).select():
        print(song.name)
