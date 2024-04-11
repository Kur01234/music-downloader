def cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="A simple yet powerful cli to download music with music-kraken.",
        epilog="This is a cli for the developers, and it is shipped with music-krakens core.\n"
               "While it is a nice and solid cli it will lack some features.\n"
               "The proper cli and other frontends will be made or already have been made.\n"
               "To see all current frontends check the docs at: https://github.com/HeIIow2/music-downloader"
    )

    # arguments for debug purposes
    parser.add_argument(
        '-v', '--verbose',
        action="store_true",
        help="Sets the logging level to debug."
    )

    parser.add_argument(
        '-m', '--force-post-process',
        action="store_true",
        help="If a to downloaded thing is skipped due to being found on disc,\nit will still update the metadata accordingly."
    )

    parser.add_argument(
        '-t', '--test',
        action="store_true",
        help="For the sake of testing. Equals: '-vp -g test'"
    )

    # general arguments
    parser.add_argument(
        '-a', '--all',
        action="store_true",
        help="If set it will download EVERYTHING the music downloader can find.\n"
             "For example weird compilations from musify."
    )

    parser.add_argument(
        '-g', '--genre',
        help="Specifies the genre. (Will be overwritten by -t)"
    )

    parser.add_argument(
        '-u', '--url',
        help="Downloads the content of given url."
    )

    parser.add_argument(
        '--settings',
        help="Opens a menu to modify the settings",
        action="store_true"
    )

    parser.add_argument(
        '-s',
        '--setting',
        help="Modifies a setting  directly.",
        nargs=2
    )

    parser.add_argument(
        "--paths",
        "-p",
        help="Prints an overview over all music-kraken paths.",
        action="store_true"
    )
    
    parser.add_argument(
        "-r",
        help="Resets the config file to the default one.",
        action="store_true"
    )
    
    parser.add_argument(
        "--frontend",
        "-f",
        help="Set a good and fast invidious/piped instance from your homecountry, to reduce the latency.",
        action="store_true"
    )

    parser.add_argument(
        "--clear-cache",
        help="Deletes the cache.",
        action="store_true"
    )

    parser.add_argument(
        "--clean-cache",
        help="Deletes the outdated cache. (all expired cached files, and not indexed files)",
        action="store_true"
    )

    arguments = parser.parse_args()

    if arguments.verbose or arguments.test:
        import logging
        print("Setting logging-level to DEBUG")
        logging.getLogger().setLevel(logging.DEBUG)

    from . import cli
    from .utils.config import read_config
    from .utils import shared
    
    if arguments.r:
        import os

        for file in shared.CONFIG_DIRECTORY.iterdir():
            if file.is_file():
                print(f"Deleting {file}....")
                file.unlink()
        read_config()
        
        exit()

    read_config()

    if arguments.setting is not None:
        cli.settings(*arguments.setting)

    if arguments.settings:
        cli.settings()

    if arguments.paths:
        cli.print_paths()
        
    if arguments.frontend:
        cli.set_frontend(silent=False)

    if arguments.clear_cache:
        from .cli.options import cache
        cache.clear_cache()

    if arguments.clean_cache:
        from .cli.options import cache
        cache.clean_cache()

    # getting the genre
    genre: str = arguments.genre
    if arguments.test:
        genre = "test"

    cli.download(
        genre=genre,
        download_all=arguments.all,
        direct_download_url=arguments.url,
        process_metadata_anyway=True or arguments.test
    )


if __name__ == "__main__":
    cli()
