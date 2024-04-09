from .config import config, read_config, write_config
from .enums.colors import BColors

"""
Here are all global important functions.
"""


def _apply_color(msg: str, color: BColors) -> str:
    if color is BColors.ENDC:
        return msg
    return color.value + msg + BColors.ENDC.value


def output(msg: str, color: BColors = BColors.ENDC):
    print(_apply_color(msg, color))


def user_input(msg: str, color: BColors = BColors.ENDC):
    return input(_apply_color(msg, color)).strip()
