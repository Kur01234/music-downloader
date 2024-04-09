import music_kraken

import logging
print("Setting logging-level to DEBUG")
logging.getLogger().setLevel(logging.DEBUG)

if __name__ == "__main__":
    commands = [
        "s: #a PTK",
        "26",
        "d: 1",
    ]

    
    music_kraken.cli.download(genre="test", command_list=commands, process_metadata_anyway=True)
    _ = "debug"