import mutagen
from mutagen.id3 import ID3, Frame, APIC
from pathlib import Path
from typing import List
import logging
from PIL import Image

from ..utils.config import logging_settings
from ..objects import Song, Target, Metadata
from ..connection import Connection

LOGGER = logging_settings["tagging_logger"]


artwork_connection: Connection = Connection()


class AudioMetadata:
    def __init__(self, file_location: str = None) -> None:
        self._file_location = None

        self.frames: ID3 = ID3()

        if file_location is not None:
            self.file_location = file_location

    def add_metadata(self, metadata: Metadata):
        for value in metadata:
            """
            https://www.programcreek.com/python/example/84797/mutagen.id3.ID3
            """
            self.frames.add(value)

    def add_song_metadata(self, song: Song):
        self.add_metadata(song.metadata)

    def save(self, file_location: Path = None):
        LOGGER.debug(f"saving following frames: {self.frames.pprint()}")

        if file_location is not None:
            self.file_location = file_location

        if self.file_location is None:
            raise Exception("no file target provided to save the data to")
        self.frames.save(self.file_location, v2_version=4)

    def set_file_location(self, file_location: Path):
        # try loading the data from the given file. if it doesn't succeed the frame remains empty
        try:
            self.frames.load(file_location, v2_version=4)
            LOGGER.debug(f"loaded following from \"{file_location}\"\n{self.frames.pprint()}")
        except mutagen.MutagenError:
            LOGGER.warning(f"couldn't find any metadata at: \"{self.file_location}\"")
        self._file_location = file_location

    file_location = property(fget=lambda self: self._file_location, fset=set_file_location)


def write_metadata_to_target(metadata: Metadata, target: Target, song: Song):
    if not target.exists:
        LOGGER.warning(f"file {target.file_path} not found")
        return

    id3_object = AudioMetadata(file_location=target.file_path)

    if song.artwork.best_variant is not None:
        r = artwork_connection.get(
            url=song.artwork.best_variant["url"],
            disable_cache=False,
        )

        temp_target: Target = Target.temp()
        with temp_target.open("wb") as f:
            f.write(r.content)

        converted_target: Target = Target.temp(name=f"{song.title}.jpeg")
        with Image.open(temp_target.file_path) as img:
            img.save(converted_target.file_path, "JPEG")

        id3_object.frames.add(
            APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=converted_target.read_bytes(),
            )
        )

        mutagen_file = mutagen.File(target.file_path)

    id3_object.add_metadata(metadata)
    id3_object.save()


def write_metadata(song: Song, ignore_file_not_found: bool = True):
    target: Target
    for target in song.target:
        if not target.exists:
            if ignore_file_not_found:
                continue
            else:
                raise ValueError(f"{song.target.file} not found")

        write_metadata_to_target(metadata=song.metadata, target=target, song=song)


def write_many_metadata(song_list: List[Song]):
    for song in song_list:
        write_metadata(song=song, ignore_file_not_found=True)
