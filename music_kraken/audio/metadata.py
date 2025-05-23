import mutagen
from mutagen.id3 import ID3, Frame, APIC, USLT
from pathlib import Path
from typing import List
import logging
from PIL import Image

from ..utils.config import logging_settings, main_settings
from ..objects import Song, Target, Metadata
from ..objects.metadata import Mapping
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
            if value is None:
                continue
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

    LOGGER.info(str(metadata))

    if song.artwork.best_variant is not None:
        best_variant = song.artwork.best_variant

        r = artwork_connection.get(
            url=best_variant["url"],
            name=song.artwork.get_variant_name(best_variant),
        )

        temp_target: Target = Target.temp()
        with temp_target.open("wb") as f:
            f.write(r.content)

        converted_target: Target = Target.temp(name=f"{song.title.replace('/', '_')}")
        with Image.open(temp_target.file_path) as img:
            # crop the image if it isn't square in the middle with minimum data loss
            width, height = img.size
            if width != height:
                if width > height:
                    img = img.crop((width // 2 - height // 2, 0, width // 2 + height // 2, height))
                else:
                    img = img.crop((0, height // 2 - width // 2, width, height // 2 + width // 2))

            # resize the image to the preferred resolution
            img.thumbnail((main_settings["preferred_artwork_resolution"], main_settings["preferred_artwork_resolution"]))

            # https://stackoverflow.com/a/59476938/16804841
            if img.mode != 'RGB':
                img = img.convert('RGB')

            img.save(converted_target.file_path, "JPEG")

        # https://stackoverflow.com/questions/70228440/mutagen-how-can-i-correctly-embed-album-art-into-mp3-file-so-that-i-can-see-t
        id3_object.frames.delall("APIC")
        id3_object.frames.add(
            APIC(
                encoding=0,
                mime="image/jpeg",
                type=3,
                desc=u"Cover",
                data=converted_target.read_bytes(),
            )
        )
        id3_object.frames.delall("USLT")
        uslt_val = metadata.get_id3_value(Mapping.UNSYNCED_LYRICS)
        id3_object.frames.add(
            USLT(encoding=3, lang=u'eng', desc=u'desc', text=uslt_val)
        )

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
