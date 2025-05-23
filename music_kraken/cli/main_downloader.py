import random
from typing import Set, Type, Dict, List
from pathlib import Path
import re

from .utils import cli_function
from .options.first_config import initial_config

from ..utils import output, BColors
from ..utils.config import write_config, main_settings
from ..utils.shared import URL_PATTERN
from ..utils.string_processing import fit_to_file_system
from ..utils.support_classes.query import Query
from ..utils.support_classes.download_result import DownloadResult
from ..utils.exception import MKInvalidInputException
from ..utils.exception.download import UrlNotFoundException
from ..utils.enums.colors import BColors
from .. import console

from ..download.results import Results, Option, PageResults, GoToResults
from ..download.page_attributes import Pages
from ..pages import Page
from ..objects import Song, Album, Artist, DatabaseObject

"""
This is the implementation of the Shell

# Behaviour

## Searching

```mkshell
> s: {querry or url}

# examples
> s: https://musify.club/release/some-random-release-183028492
> s: r: #a an Artist #r some random Release
```

Searches for an url, or an query

### Query Syntax

```
#a {artist} #r {release} #t {track}
```

You can escape stuff like `#` doing this: `\#`

## Downloading

To download something, you either need a direct link, or you need to have already searched for options

```mkshell
> d: {option ids or direct url}

# examples
> d: 0, 3, 4
> d: 1
> d: https://musify.club/release/some-random-release-183028492
```

## Misc

### Exit

```mkshell
> q
> quit
> exit
> abort
```

### Current Options

```mkshell
> .
```

### Previous Options

```
> ..
```

"""

EXIT_COMMANDS = {"q", "quit", "exit", "abort"}
ALPHABET = "abcdefghijklmnopqrstuvwxyz"
PAGE_NAME_FILL = "-"
MAX_PAGE_LEN = 21


def get_existing_genre() -> List[str]:
    """
    gets the name of all subdirectories of shared.MUSIC_DIR,
    but filters out all directories, where the name matches with any patern
    from shared.NOT_A_GENRE_REGEX.
    """
    existing_genres: List[str] = []

    # get all subdirectories of MUSIC_DIR, not the files in the dir.
    existing_subdirectories: List[Path] = [f for f in main_settings["music_directory"].iterdir() if f.is_dir()]

    for subdirectory in existing_subdirectories:
        name: str = subdirectory.name

        if not any(re.match(regex_pattern, name) for regex_pattern in main_settings["not_a_genre_regex"]):
            existing_genres.append(name)

    existing_genres.sort()

    return existing_genres


def get_genre():
    existing_genres = get_existing_genre()
    for i, genre_option in enumerate(existing_genres):
        print(f"{i + 1:0>2}: {genre_option}")

    while True:
        genre = input("Id or new genre: ")

        if genre.isdigit():
            genre_id = int(genre) - 1
            if genre_id >= len(existing_genres):
                print(f"No genre under the id {genre_id + 1}.")
                continue

            return existing_genres[genre_id]

        new_genre = fit_to_file_system(genre)

        agree_inputs = {"y", "yes", "ok"}
        verification = input(f"create new genre \"{new_genre}\"? (Y/N): ").lower()
        if verification in agree_inputs:
            return new_genre


def help_message():
    print()
    print(random.choice(main_settings["happy_messages"]))
    print()


class Downloader:
    def __init__(
            self,
            exclude_pages: Set[Type[Page]] = None,
            exclude_shady: bool = False,
            max_displayed_options: int = 10,
            option_digits: int = 3,
            genre: str = None,
            process_metadata_anyway: bool = False,
    ) -> None:
        self.pages: Pages = Pages(exclude_pages=exclude_pages, exclude_shady=exclude_shady)

        self.page_dict: Dict[str, Type[Page]] = dict()

        self.max_displayed_options = max_displayed_options
        self.option_digits: int = option_digits

        self.current_results: Results = None
        self._result_history: List[Results] = []

        self.genre = genre or get_genre()
        self.process_metadata_anyway = process_metadata_anyway

        output()
        output(f"Downloading to: \"{self.genre}\"", color=BColors.HEADER)
        output()

    def print_current_options(self):
        self.page_dict = dict()

        print()

        page_count = 0
        for option in self.current_results.formatted_generator():
            if isinstance(option, Option):
                r = f"{BColors.GREY.value}{option.index:0{self.option_digits}}{BColors.ENDC.value} {option.music_object.option_string}"
                print(r)
            else:
                prefix = ALPHABET[page_count % len(ALPHABET)]
                print(
                    f"{BColors.HEADER.value}({prefix}) --------------------------------{option.__name__:{PAGE_NAME_FILL}<{MAX_PAGE_LEN}}--------------------{BColors.ENDC.value}")

                self.page_dict[prefix] = option
                self.page_dict[option.__name__] = option

                page_count += 1

        print()

    def set_current_options(self, current_options: Results):
        if main_settings["result_history"]:
            self._result_history.append(current_options)

        if main_settings["history_length"] != -1:
            if len(self._result_history) > main_settings["history_length"]:
                self._result_history.pop(0)

        self.current_results = current_options

    def previous_option(self) -> bool:
        if not main_settings["result_history"]:
            print("History is turned of.\nGo to main_settings, and change the value at 'result_history' to 'true'.")
            return False

        if len(self._result_history) <= 1:
            print(f"No results in history.")
            return False
        self._result_history.pop()
        self.current_results = self._result_history[-1]
        return True

    def _process_parsed(self, key_text: Dict[str, str], query: str) -> Query:
        # strip all the values in key_text
        key_text = {key: value.strip() for key, value in key_text.items()}

        song = None if not "t" in key_text else Song(title=key_text["t"], dynamic=True)
        album = None if not "r" in key_text else Album(title=key_text["r"], dynamic=True)
        artist = None if not "a" in key_text else Artist(name=key_text["a"], dynamic=True)

        if song is not None:
            if album is not None:
                song.album_collection.append(album)
            if artist is not None:
                song.artist_collection.append(artist)
            return Query(raw_query=query, music_object=song)

        if album is not None:
            if artist is not None:
                album.artist_collection.append(artist)
            return Query(raw_query=query, music_object=album)

        if artist is not None:
            return Query(raw_query=query, music_object=artist)

        return Query(raw_query=query)

    def search(self, query: str):
        if re.match(URL_PATTERN, query) is not None:
            try:
                page, data_object = self.pages.fetch_url(query)
            except UrlNotFoundException as e:
                print(f"{e.url} could not be attributed/parsed to any yet implemented site.\n"
                      f"PR appreciated if the site isn't implemented.\n"
                      f"Recommendations and suggestions on sites to implement appreciated.\n"
                      f"But don't be a bitch if I don't end up implementing it.")
                return
            self.set_current_options(PageResults(page, data_object.options, max_items_per_page=self.max_displayed_options))
            self.print_current_options()
            return

        special_characters = "#\\"
        query = query + " "

        key_text = {}

        skip_next = False
        escape_next = False
        new_text = ""
        latest_key: str = None
        for i in range(len(query) - 1):
            current_char = query[i]
            next_char = query[i + 1]

            if skip_next:
                skip_next = False
                continue

            if escape_next:
                new_text += current_char
                escape_next = False

            # escaping
            if current_char == "\\":
                if next_char in special_characters:
                    escape_next = True
                    continue

            if current_char == "#":
                if latest_key is not None:
                    key_text[latest_key] = new_text
                    new_text = ""

                latest_key = next_char
                skip_next = True
                continue

            new_text += current_char

        if latest_key is not None:
            key_text[latest_key] = new_text

        parsed_query: Query = self._process_parsed(key_text, query)

        self.set_current_options(self.pages.search(parsed_query))
        self.print_current_options()

    def goto(self, data_object: DatabaseObject):
        page: Type[Page]

        self.pages.fetch_details(data_object, stop_at_level=1)

        self.set_current_options(GoToResults(data_object.options, max_items_per_page=self.max_displayed_options))

        self.print_current_options()

    def download(self, data_objects: List[DatabaseObject], **kwargs) -> bool:
        output()
        if len(data_objects) > 1:
            output(f"Downloading  {len(data_objects)} objects...", *("- " + o.option_string for o in data_objects), color=BColors.BOLD, sep="\n")

        _result_map: Dict[DatabaseObject, DownloadResult] = dict()

        for database_object in data_objects:
            r = self.pages.download(
                data_object=database_object, 
                genre=self.genre, 
                **kwargs
            )
            _result_map[database_object] = r

        for music_object, result in _result_map.items():
            output()
            output(music_object.option_string)
            output(result)

        return True

    def process_input(self, input_str: str) -> bool:
        try:
            input_str = input_str.strip()
            processed_input: str = input_str.lower()

            if processed_input in EXIT_COMMANDS:
                return True

            if processed_input == ".":
                self.print_current_options()
                return False

            if processed_input == "..":
                if self.previous_option():
                    self.print_current_options()
                return False

            command = ""
            query = processed_input
            if ":" in processed_input:
                _ = processed_input.split(":")
                command, query = _[0], ":".join(_[1:])

            do_search = "s" in command
            do_fetch = "f" in command
            do_download = "d" in command
            do_merge = "m" in command

            if do_search and (do_download or do_fetch or do_merge):
                raise MKInvalidInputException(message="You can't search and do another operation at the same time.")

            if do_search:
                self.search(":".join(input_str.split(":")[1:]))
                return False

            def get_selected_objects(q: str):
                if q.strip().lower() == "all":
                    return list(self.current_results)

                indices = []
                for possible_index in q.split(","):
                    possible_index = possible_index.strip()
                    if possible_index == "":
                        continue
                    
                    i = 0
                    try:
                        i = int(possible_index)
                    except ValueError:
                        raise MKInvalidInputException(message=f"The index \"{possible_index}\" is not a number.")

                    if i < 0 or i >= len(self.current_results):
                        raise MKInvalidInputException(message=f"The index \"{i}\" is not within the bounds of 0-{len(self.current_results) - 1}.")
                    
                    indices.append(i)

                return [self.current_results[i] for i in indices]

            selected_objects = get_selected_objects(query)

            if do_merge:
                old_selected_objects = selected_objects

                a = old_selected_objects[0]
                for b in old_selected_objects[1:]:
                    if type(a) != type(b):
                        raise MKInvalidInputException(message="You can't merge different types of objects.")
                    a.merge(b)

                selected_objects = [a]

            if do_fetch:
                for data_object in selected_objects:
                    self.pages.fetch_details(data_object)

                self.print_current_options()
                return False

            if do_download:
                self.download(selected_objects)
                return False

            if len(selected_objects) != 1:
                raise MKInvalidInputException(message="You can only go to one object at a time without merging.")

            self.goto(selected_objects[0])
            return False
        except MKInvalidInputException as e:
            output("\n" + e.message + "\n", color=BColors.FAIL)
            help_message()

        return False

    def mainloop(self):
        while True:
            if self.process_input(input("> ")):
                return


@cli_function
def download(
        genre: str = None,
        download_all: bool = False,
        direct_download_url: str = None,
        command_list: List[str] = None,
        process_metadata_anyway: bool = False,
):
    if main_settings["hasnt_yet_started"]:
        code = initial_config()
        if code == 0:
            main_settings["hasnt_yet_started"] = False
            write_config()
            print(f"{BColors.OKGREEN.value}Restart the programm to use it.{BColors.ENDC.value}")
        else:
            print(f"{BColors.FAIL.value}Something went wrong configuring.{BColors.ENDC.value}")

    shell = Downloader(genre=genre, process_metadata_anyway=process_metadata_anyway)

    if command_list is not None:
        for command in command_list:
            shell.process_input(command)
        return

    if direct_download_url is not None:
        if shell.download(direct_download_url, download_all=download_all):
            return

    shell.mainloop()
