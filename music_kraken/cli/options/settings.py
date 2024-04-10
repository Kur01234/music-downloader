from ..utils import cli_function

from ...utils.config import config, write_config
from ...utils import exception


def modify_setting(_name: str, _value: str, invalid_ok: bool = True) -> bool:
    try:
        config.set_name_to_value(_name, _value)
    except exception.config.SettingException as e:
        if invalid_ok:
            print(e)
            return False
        else:
            raise e

    write_config()
    return True


def print_settings():
    for i, attribute in enumerate(config):
        print(f"{i:0>2}: {attribute.name}={attribute.value}")
        
        
    def modify_setting_by_index(index: int) -> bool:
        attribute = list(config)[index]

        print()
        print(attribute)

        input__ = input(f"{attribute.name}=")
        if not modify_setting(attribute.name, input__.strip()):
            return modify_setting_by_index(index)

        return True


def modify_setting_by_index(index: int) -> bool:
    attribute = list(config)[index]

    print()
    print(attribute)

    input__ = input(f"{attribute.name}=")
    if not modify_setting(attribute.name, input__.strip()):
        return modify_setting_by_index(index)

    return True


@cli_function
def settings(
        name: str = None,
        value: str = None,
):
    if name is not None and value is not None:
        modify_setting(name, value, invalid_ok=True)
        return

    while True:
        print_settings()

        input_ = input("Id of setting to modify: ")
        print()
        if input_.isdigit() and int(input_) < len(config):
            if modify_setting_by_index(int(input_)):
                return
        else:
            print("Please input a valid ID.")
            print()