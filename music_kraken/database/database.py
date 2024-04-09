# Standard library
from typing import Optional, Union, List
from enum import Enum
from playhouse.migrate import *

# third party modules
from peewee import (
    SqliteDatabase,
    MySQLDatabase,
    PostgresqlDatabase,
)

# own modules
from . import (
    data_models,
    write
)
from .. import objects


class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"

class Database:
    database: Union[SqliteDatabase, PostgresqlDatabase, MySQLDatabase]

    def __init__(
            self,
            db_type: DatabaseType,
            db_name: str,
            db_user: Optional[str] = None,
            db_password: Optional[str] = None,
            db_host: Optional[str] = None,
            db_port: Optional[int] = None
    ):
        self.db_type = db_type
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_port = db_port

        self.initialize_database()

    def create_database(self) -> Union[SqliteDatabase, PostgresqlDatabase, MySQLDatabase]:
        """Create a database instance based on the configured database type and parameters.

        Returns:
            The created database instance, or None if an invalid database type was specified.
        """

        # SQLITE
        if self.db_type == DatabaseType.SQLITE:
            return SqliteDatabase(self.db_name)

        # POSTGRES
        if self.db_type == DatabaseType.POSTGRESQL:
            return PostgresqlDatabase(
                self.db_name,
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port,
            )

        # MYSQL
        if self.db_type == DatabaseType.MYSQL:
            return MySQLDatabase(
                self.db_name,
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port,
            )

        raise ValueError("Invalid database type specified.")


    @property
    def migrator(self) -> SchemaMigrator:
        if self.db_type == DatabaseType.SQLITE:
            return SqliteMigrator(self.database)
        
        if self.db_type == DatabaseType.MYSQL:
            return MySQLMigrator(self.database)
    
        if self.db_type == DatabaseType.POSTGRESQL:
            return PostgresqlMigrator(self.database)

    def initialize_database(self):
        """
        Connect to the database
        initialize the previously defined databases
        create tables if they don't exist.
        """
        self.database = self.create_database()
        self.database.connect()
        
        migrator = self.migrator
        
        for model in data_models.ALL_MODELS:
            model = model.Use(self.database)
            
            if self.database.table_exists(model):
                migration_operations = [
                    migrator.add_column(
                        "some field", field[0], field[1]
                    )
                    for field in model._meta.fields.items()
                ]
                
                migrate(*migration_operations)
            else:
                self.database.create_tables([model], safe=True)

        #self.database.create_tables([model.Use(self.database) for model in data_models.ALL_MODELS], safe=True)

        """
        upgrade old databases. 
        If a collumn has been added in a new version this adds it to old Tables, 
        without deleting the data in legacy databases
        """
        
        for model in data_models.ALL_MODELS:
            model = model.Use(self.database)
            
            
            
            print(model._meta.fields)

    def push(self, database_object: objects.DatabaseObject):
        """
        Adds a new music object to the database using the corresponding method from the `write` session.
        When possible, rather use the `push_many` function.
        This gets even more important, when using a remote database server.

        Args:
            database_object (objects.MusicObject): The music object to add to the database.

        Returns:
            The newly added music object.
        """

        with write.WritingSession(self.database) as writing_session:
            if isinstance(database_object, objects.Song):
                return writing_session.add_song(database_object)
            
            if isinstance(database_object, objects.Album):
                return writing_session.add_album(database_object)
            
            if isinstance(database_object, objects.Artist):
                return writing_session.add_artist(database_object)

    def push_many(self, database_objects: List[objects.DatabaseObject]) -> None:
        """
        Adds a list of MusicObject instances to the database.
        This function sends only needs one querry for each type of table added.
        Beware that if you have for example an object like this:
        - Album
        - Song
        - Song
        you already have 3 different Tables.
    
        Unlike the function `push`, this function doesn't return the added database objects.

        Args:
            database_objects: List of MusicObject instances to be added to the database.
        """

        with write.WritingSession(self.database) as writing_session:
            for obj in database_objects:
                if isinstance(obj, objects.Song):
                    writing_session.add_song(obj)
                    continue
                
                if isinstance(obj, objects.Album):
                    writing_session.add_album(obj)
                    continue
                
                if isinstance(obj, objects.Artist):
                    writing_session.add_artist(obj)
                    continue


    def __del__(self):
        self.database.close()
