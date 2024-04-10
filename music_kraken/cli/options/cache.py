from logging import getLogger

from ..utils import cli_function
from ...connection.cache import Cache


@cli_function
def clear_cache():
    """
    Deletes the cache.
    :return:
    """

    Cache("main", getLogger("cache")).clear()
    print("Cleared cache")


@cli_function
def clean_cache():
    """
    Deletes the outdated cache. (all expired cached files, and not indexed files)
    :return:
    """

    Cache("main", getLogger("cache")).clean()
    print("Cleaned cache")
