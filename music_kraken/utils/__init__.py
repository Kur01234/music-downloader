from datetime import datetime
from pathlib import Path
import json
import logging
import inspect
from typing import List, Union

from .shared import DEBUG, DEBUG_LOGGING, DEBUG_DUMP, DEBUG_TRACE, DEBUG_OBJECT_TRACE, DEBUG_OBJECT_TRACE_CALLSTACK
from .config import config, read_config, write_config
from .enums.colors import BColors
from .path_manager import LOCATIONS
from .hacking import merge_args

"""
IO functions
"""

def _apply_color(msg: str, color: BColors) -> str:
    if not isinstance(msg, str):
        msg = str(msg)

    endc = BColors.ENDC.value

    if color is BColors.ENDC:
        return msg

    msg = msg.replace(BColors.ENDC.value, BColors.ENDC.value + color.value)

    return color.value + msg + BColors.ENDC.value


@merge_args(print)
def output(*msg: List[str], color: BColors = BColors.ENDC, **kwargs):
    print(*(_apply_color(s, color) for s in msg), **kwargs)


def user_input(msg: str, color: BColors = BColors.ENDC):
    return input(_apply_color(msg, color)).strip()


def dump_to_file(file_name: str, payload: str, is_json: bool = False, exit_after_dump: bool = False):
    if not DEBUG_DUMP:
        return

    path = Path(LOCATIONS.TEMP_DIRECTORY, file_name)
    logging.warning(f"dumping {file_name} to: \"{path}\"")

    if is_json and isinstance(payload, str):
        payload = json.loads(payload)

    if isinstance(payload, dict):
        payload = json.dumps(payload, indent=4)

    with path.open("w") as f:
        f.write(payload)

    if exit_after_dump:
        exit()


def trace(msg: str):
    if not DEBUG_TRACE:
        return

    output(BColors.OKBLUE.value + "trace: " + BColors.ENDC.value + msg)

def request_trace(msg: str):
    if not DEBUG_TRACE:
        return

    output(BColors.OKGREEN.value + "request: " + BColors.ENDC.value + msg)

def object_trace(obj):
    if not DEBUG_OBJECT_TRACE:
        return

    appendix =  f" called by [{' | '.join(f'{s.function} {Path(s.filename).name}:{str(s.lineno)}' for s in inspect.stack()[1:5])}]" if DEBUG_OBJECT_TRACE_CALLSTACK else ""
    output("object: " + str(obj) + appendix)


"""
misc functions
"""

def traverse_json_path(data, path: Union[str, List[str]], default=None):
    """
    Path parts are concatenated with . or wrapped with [""] for object keys and wrapped in [] for array indices.
    """

    if isinstance(path, str):
        path = path.replace('["', '.').replace('"]', '.').replace("[", ".").replace("]", ".")
        path = [p for p in path.split(".") if len(p) > 0]

    if len(path) <= 0:
        return data

    current = path[0]
    path = path[1:]

    new_data = None

    if isinstance(data, dict):        
        new_data = data.get(current)

    elif isinstance(data, list):
        try:
            new_data = data[int(current)]
        except (IndexError, ValueError):
            pass

    if new_data is None:
        return default

    return traverse_json_path(data=new_data, path=path, default=default)

_auto_increment = 0
def generate_id() -> int:
    global _auto_increment
    _auto_increment += 1
    return _auto_increment
    
def get_current_millis() -> int:
    dt = datetime.now()
    return int(dt.microsecond / 1_000)


def get_unix_time() -> int:
    return int(datetime.now().timestamp())