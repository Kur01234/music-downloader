from dataclasses import dataclass, field
from typing import List, Tuple

from ...utils.config import main_settings, logging_settings
from ...utils.enums.colors import BColors
from ...objects import Target

UNIT_PREFIXES: List[str] = ["", "k", "m", "g", "t"]
UNIT_DIVISOR = 1024

LOGGER = logging_settings["download_logger"]


@dataclass
class DownloadResult:
    total: int = 0
    fail: int = 0
    sponsor_segments: int = 0
    error_message: str = None
    total_size = 0
    found_on_disk: int = 0

    _error_message_list: List[str] = field(default_factory=list)

    @property
    def success(self) -> int:
        return self.total - self.fail

    @property
    def success_percentage(self) -> float:
        if self.total == 0:
            return 0
        return self.success / self.total

    @property
    def failure_percentage(self) -> float:
        if self.total == 0:
            return 1
        return self.fail / self.total

    @property
    def is_fatal_error(self) -> bool:
        return self.error_message is not None

    @property
    def is_mild_failure(self) -> bool:
        if self.is_fatal_error:
            return True

        return self.failure_percentage > main_settings["show_download_errors_threshold"]

    def _size_val_unit_pref_ind(self, val: float, ind: int) -> Tuple[float, int]:
        if val < UNIT_DIVISOR:
            return val, ind
        if ind >= len(UNIT_PREFIXES):
            return val, ind

        return self._size_val_unit_pref_ind(val=val / UNIT_DIVISOR, ind=ind + 1)

    @property
    def formated_size(self) -> str:
        total_size, prefix_index = self._size_val_unit_pref_ind(self.total_size, 0)
        return f"{total_size:.{2}f} {UNIT_PREFIXES[prefix_index]}B"

    def add_target(self, target: Target):
        self.total_size += target.size

    def merge(self, other: "DownloadResult"):
        if other.is_fatal_error:
            LOGGER.debug(other.error_message)
            self._error_message_list.append(other.error_message)
            self.total += 1
            self.fail += 1
        else:
            self.total += other.total
            self.fail += other.fail
            self._error_message_list.extend(other._error_message_list)

        self.sponsor_segments += other.sponsor_segments
        self.total_size += other.total_size
        self.found_on_disk += other.found_on_disk

    def __str__(self):
        if self.is_fatal_error:
            return self.error_message
        head = f"{self.fail} from {self.total} downloads failed:\n" \
               f"success-rate:\t{int(self.success_percentage * 100)}%\n" \
               f"fail-rate:\t{int(self.failure_percentage * 100)}%\n" \
               f"total size:\t{self.formated_size}\n" \
               f"skipped segments:\t{self.sponsor_segments}\n" \
               f"found on disc:\t{self.found_on_disk}"

        if not self.is_mild_failure:
            return head

        _lines = [head]
        _lines.extend(BColors.FAIL.value + s + BColors.ENDC.value for s in self._error_message_list)
        return "\n".join(_lines)
