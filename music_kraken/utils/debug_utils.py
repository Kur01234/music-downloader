from pathlib import Path
import json

from .path_manager import LOCATIONS


def dump_to_file(file_name: str, payload: str, is_json: bool = False, exit_after_dump: bool = True):
    path = Path(LOCATIONS.TEMP_DIRECTORY, file_name)
    print(f"Dumping payload to: \"{path}\"")

    if is_json:
        payload = json.dumps(json.loads(payload), indent=4)

    if isinstance(payload, dict):
        payload = json.dumps(payload, indent=4)

    with path.open("w") as f:
        f.write(payload)

    if exit_after_dump:
        exit()
