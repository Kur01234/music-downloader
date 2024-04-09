from pathlib import Path

import platformdirs


def get_config_directory(application_name: str) -> Path:
    return platformdirs.user_config_path(appname=application_name)
