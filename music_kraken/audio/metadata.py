import mutagen
from mutagen.id3 import ID3, Frame
from pathlib import Path
from typing import List
import logging

from ..utils.config import logging_settings
from ..objects import Song, Target, Metadata


LOGGER = logging_settings["tagging_logger"]


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


def write_metadata_to_target(metadata: Metadata, target: Target):
    if not target.exists:
        return

    id3_object = AudioMetadata(file_location=target.file_path)
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

        id3_object = AudioMetadata(file_location=target.file_path)
        id3_object.add_song_metadata(song=song)
        id3_object.save()


def write_many_metadata(song_list: List[Song]):
    for song in song_list:
        write_metadata(song=song, ignore_file_not_found=True)


if __name__ == "__main__":
    print("called directly")
    filepath = "/home/lars/Music/deathcore/Archspire/Bleed the Future/Bleed the Future.mp3"

    audio_metadata = AudioMetadata(file_location=filepath)
    print(audio_metadata.frames.pprint())
