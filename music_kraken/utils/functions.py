import os
from datetime import datetime


def clear_console():
    os.system('cls' if os.name in ('nt', 'dos') else 'clear')


def get_current_millis() -> int:
    dt = datetime.now()
    return int(dt.microsecond / 1_000)
