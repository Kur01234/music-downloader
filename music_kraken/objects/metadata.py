from enum import Enum
from typing import List, Dict, Tuple

from mutagen import id3
import datetime


class Mapping(Enum):
    """
    These frames belong to the id3 standart
    https://web.archive.org/web/20220830091059/https://id3.org/id3v2.4.0-frames
    https://id3lib.sourceforge.net/id3/id3v2com-00.html
    https://mutagen-specs.readthedocs.io/en/latest/id3/id3v2.4.0-frames.html
    """
    # Textframes
    TITLE = "TIT2"
    ISRC = "TSRC"
    LENGTH = "TLEN"  # in milliseconds
    # The 'Date' frame is a numeric string in the DDMM format containing the date for the recording. This field is always four characters long.
    DATE = "TDAT"
    # The 'Time' frame is a numeric string in the HHMM format containing the time for the recording. This field is always four characters long.
    TIME = "TIME"
    YEAR = "TYER"
    TRACKNUMBER = "TRCK"
    TOTALTRACKS = "TRCK"  # Stored in the same frame with TRACKNUMBER, separated by '/': e.g. '4/9'.
    TITLESORTORDER = "TSOT"
    ENCODING_SETTINGS = "TSSE"
    SUBTITLE = "TIT3"
    SET_SUBTITLE = "TSST"
    RELEASE_DATE = "TDRL"
    RECORDING_DATES = "TXXX"
    PUBLISHER_URL = "WPUB"
    PUBLISHER = "TPUB"
    RATING = "POPM"
    DISCNUMBER = "TPOS"
    MOVEMENT_COUNT = "MVIN"
    TOTALDISCS = "TPOS"
    ORIGINAL_RELEASE_DATE = "TDOR"
    ORIGINAL_ARTIST = "TOPE"
    ORIGINAL_ALBUM = "TOAL"
    MEDIA_TYPE = "TMED"
    LYRICIST = "TEXT"
    WRITER = "TEXT"
    ARTIST = "TPE1"
    LANGUAGE = "TLAN"  # https://en.wikipedia.org/wiki/ISO_639-2
    ITUNESCOMPILATION = "TCMP"
    REMIXED_BY = "TPE4"
    RADIO_STATION_OWNER = "TRSO"
    RADIO_STATION = "TRSN"
    INITIAL_KEY = "TKEY"
    OWNER = "TOWN"
    ENCODED_BY = "TENC"
    COPYRIGHT = "TCOP"
    GENRE = "TCON"
    GROUPING = "TIT1"
    CONDUCTOR = "TPE3"
    COMPOSERSORTORDER = "TSOC"
    COMPOSER = "TCOM"
    BPM = "TBPM"
    ALBUM_ARTIST = "TPE2"
    BAND = "TPE2"
    ARTISTSORTORDER = "TSOP"
    ALBUM = "TALB"
    ALBUMSORTORDER = "TSOA"
    ALBUMARTISTSORTORDER = "TSO2"
    TAGGING_TIME = "TDTG"

    SOURCE_WEBPAGE_URL = "WOAS"
    FILE_WEBPAGE_URL = "WOAF"
    INTERNET_RADIO_WEBPAGE_URL = "WORS"
    ARTIST_WEBPAGE_URL = "WOAR"
    COPYRIGHT_URL = "WCOP"
    COMMERCIAL_INFORMATION_URL = "WCOM"
    PAYMEMT_URL = "WPAY"

    MOVEMENT_INDEX = "MVIN"
    MOVEMENT_NAME = "MVNM"

    UNSYNCED_LYRICS = "USLT"
    COMMENT = "COMM"

    @classmethod
    def get_text_instance(cls, key: str, value: str):
        return id3.Frames[key](encoding=3, text=value)

    @classmethod
    def get_url_instance(cls, key: str, url: str):
        return id3.Frames[key](encoding=3, url=url)

    @classmethod
    def get_mutagen_instance(cls, attribute, value):
        key = attribute.value

        if key[0] == 'T':
            # a text field
            return cls.get_text_instance(key, value)
        if key[0] == "W":
            # an url field
            return cls.get_url_instance(key, value)


class ID3Timestamp:
    def __init__(
            self,
            year: int = None,
            month: int = None,
            day: int = None,
            hour: int = None,
            minute: int = None,
            second: int = None
    ):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second

        self.has_year = year is not None
        self.has_month = month is not None
        self.has_day = day is not None
        self.has_hour = hour is not None
        self.has_minute = minute is not None
        self.has_second = second is not None

        if not self.has_year:
            year = 1
        if not self.has_month:
            month = 1
        if not self.has_day:
            day = 1
        if not self.has_hour:
            hour = 1
        if not self.has_minute:
            minute = 1
        if not self.has_second:
            second = 1

        self.date_obj = datetime.datetime(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second
        )
        
    def __hash__(self):
        return self.date_obj.__hash__()

    def __lt__(self, other):
        return self.date_obj < other.date_obj

    def __le__(self, other):
        return self.date_obj <= other.date_obj

    def __gt__(self, other):
        return self.date_obj > other.date_obj

    def __ge__(self, other):
        return self.date_obj >= other.date_obj

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self.date_obj == other.date_obj

    def get_time_format(self) -> str:
        """
        https://mutagen-specs.readthedocs.io/en/latest/id3/id3v2.4.0-structure.html

        The timestamp fields are based on a subset of ISO 8601. When being as precise as possible the format of a
        time string is
         - yyyy-MM-ddTHH:mm:ss
         - (year[%Y], “-”, month[%m], “-”, day[%d], “T”, hour (out of 24)[%H], ”:”, minutes[%M], ”:”, seconds[%S])
         - %Y-%m-%dT%H:%M:%S
        but the precision may be reduced by removing as many time indicators as wanted. Hence valid timestamps are
         - yyyy
         - yyyy-MM
         - yyyy-MM-dd
         - yyyy-MM-ddTHH
         - yyyy-MM-ddTHH:mm
         - yyyy-MM-ddTHH:mm:ss
        All time stamps are UTC. For durations, use the slash character as described in 8601,
        and for multiple non-contiguous dates, use multiple strings, if allowed by the frame definition.

        :return timestamp: as timestamp in the format of the id3 time as above described
        """

        if self.has_year and self.has_month and self.has_day and self.has_hour and self.has_minute and self.has_second:
            return "%Y-%m-%dT%H:%M:%S"
        if self.has_year and self.has_month and self.has_day and self.has_hour and self.has_minute:
            return "%Y-%m-%dT%H:%M"
        if self.has_year and self.has_month and self.has_day and self.has_hour:
            return "%Y-%m-%dT%H"
        if self.has_year and self.has_month and self.has_day:
            return "%Y-%m-%d"
        if self.has_year and self.has_month:
            return "%Y-%m"
        if self.has_year:
            return "%Y"
        return ""

    def get_timestamp(self) -> str:
        time_format = self.get_time_format()
        return self.date_obj.strftime(time_format)

    def get_timestamp_w_format(self) -> Tuple[str, str]:
        time_format = self.get_time_format()
        return time_format, self.date_obj.strftime(time_format)

    @classmethod
    def fromtimestamp(cls, utc_timestamp: int):
        date_obj = datetime.datetime.fromtimestamp(utc_timestamp)

        return cls(
            year=date_obj.year,
            month=date_obj.month,
            day=date_obj.day,
            hour=date_obj.hour,
            minute=date_obj.minute,
            second=date_obj.second
        )

    @classmethod
    def strptime(cls, time_stamp: str, format: str):
        """
        day: "%d" 
        month: "%b", "%B", "%m"
        year: "%y", "%Y"
        hour: "%H", "%I"
        minute: "%M"
        second: "%S"
        """
        date_obj = datetime.datetime.strptime(time_stamp, format)

        day = None
        if "%d" in format:
            day = date_obj.day
        month = None
        if any([i in format for i in ("%b", "%B", "%m")]):
            month = date_obj.month
        year = None
        if any([i in format for i in ("%y", "%Y")]):
            year = date_obj.year
        hour = None
        if any([i in format for i in ("%H", "%I")]):
            hour = date_obj.hour
        minute = None
        if "%M" in format:
            minute = date_obj.minute
        second = None
        if "%S" in format:
            second = date_obj.second

        return cls(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second
        )

    @classmethod
    def now(cls):
        date_obj = datetime.datetime.now()

        return cls(
            year=date_obj.year,
            month=date_obj.month,
            day=date_obj.day,
            hour=date_obj.hour,
            minute=date_obj.minute,
            second=date_obj.second
        )

    def strftime(self, format: str) -> str:
        return self.date_obj.strftime(format)

    def __str__(self) -> str:
        return self.timestamp

    def __repr__(self) -> str:
        return self.timestamp

    timestamp: str = property(fget=get_timestamp)
    timeformat: str = property(fget=get_time_format)


class Metadata:
    # it's a null byte for the later concatenation of text frames
    NULL_BYTE: str = "\x00"
    # this is pretty self-explanatory
    # the key is an enum from Mapping
    # the value is a list with each value
    # the mutagen object for each frame will be generated dynamically
    id3_dict: Dict[Mapping, list]

    def __init__(self, id3_dict: Dict[any, list] = None) -> None:
        self.id3_dict = dict()
        if id3_dict is not None:
            self.add_metadata_dict(id3_dict)

    def __setitem__(self, frame: Mapping, value_list: list, override_existing: bool = True):
        if type(value_list) != list:
            raise ValueError(f"can only set attribute to list, not {type(value_list)}")

        new_val = [i for i in value_list if i not in {None, ''}]

        if len(new_val) == 0:
            return

        if override_existing:
            self.id3_dict[frame] = new_val
        else:
            if frame not in self.id3_dict:
                self.id3_dict[frame] = new_val
                return

            self.id3_dict[frame].extend(new_val)

    def __getitem__(self, key):
        if key not in self.id3_dict:
            return None
        return self.id3_dict[key]

    def delete_field(self, key: str):
        if key in self.id3_dict:
            return self.id3_dict.pop(key)

    def add_metadata_dict(self, metadata_dict: dict, override_existing: bool = True):
        for field_enum, value in metadata_dict.items():
            self.__setitem__(field_enum, value, override_existing=override_existing)

    def merge(self, other, override_existing: bool = False):
        """
        adds the values of another metadata obj to this one

        other is a value of the type MetadataAttribute.Metadata
        """

        self.add_metadata_dict(other.id3_dict, override_existing=override_existing)

    def merge_many(self, many_other):
        """
        adds the values of many other metadata objects to this one
        """

        for other in many_other:
            self.merge(other)

    def get_id3_value(self, field):
        if field not in self.id3_dict:
            return None

        list_data = self.id3_dict[field]
        #correct duplications
        correct_list_data = list()
        for data in list_data:
            if data not in correct_list_data:
                correct_list_data.append(data)
        list_data = correct_list_data
        # convert for example the time objects to timestamps
        for i, element in enumerate(list_data):
            # for performance’s sake I don't do other checks if it is already the right type
            if type(element) == str:
                continue

            if type(element) in {int}:
                list_data[i] = str(element)

            if type(element) == ID3Timestamp:
                list_data[i] = element.timestamp
                continue
            
        """
        Version 2.4 of the specification prescribes that all text fields (the fields that start with a T, except for TXXX) can contain multiple values separated by a null character. 
        Thus if above conditions are met, I concatenate the list,
        else I take the first element
        """
        if field.value[0].upper() == "T" and field.value.upper() != "TXXX":
            return self.NULL_BYTE.join(list_data)
        
        return list_data[0]

    def get_mutagen_object(self, field):
        return Mapping.get_mutagen_instance(field, self.get_id3_value(field))

    def __str__(self) -> str:
        rows = []
        for key, value in self.id3_dict.items():
            rows.append(f"{key} - {str(value)}")
        return "\n".join(rows)

    def __iter__(self):
        """
        returns a generator, you can iterate through,
        to directly tagg a file with id3 container.
        """
        # set the tagging timestamp to the current time
        self.__setitem__(Mapping.TAGGING_TIME, [ID3Timestamp.now()])
        for field in self.id3_dict:
            yield self.get_mutagen_object(field)
