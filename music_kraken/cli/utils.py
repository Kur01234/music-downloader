from ..utils.shared import get_random_message


def cli_function(function):
    def wrapper(*args, **kwargs):
        silent = kwargs.get("no_cli", False)
        if "no_cli" in kwargs:
            del kwargs["no_cli"]
        
        if silent:
            return function(*args, **kwargs)
            return
        
        code = 0
        
        print_cute_message()
        print()
        try:
            code = function(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n\nRaise an issue if I fucked up:\nhttps://github.com/HeIIow2/music-downloader/issues")

        finally:
            print()
            print_cute_message()
            print("See you soon! :3")
        
        exit()
            
    return wrapper


def print_cute_message():
    message = get_random_message()
    try:
        print(message)
    except UnicodeEncodeError:
        message = str(c for c in message if 0 < ord(c) < 127)
        print(message)


    