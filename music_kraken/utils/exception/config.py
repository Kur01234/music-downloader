class SettingException(Exception):
    pass


class SettingNotFound(SettingException):
    def __init__(self, setting_name: str):
        self.setting_name = setting_name

    def __str__(self):
        return f"Setting '{self.setting_name}' not found."


class SettingValueError(SettingException):
    def __init__(self, setting_name: str, setting_value: str, rule: str):
        """
        The rule has to be such, that the following format makes sense:
        {name} {rule}, not '{value}'

        :param setting_name:
        :param setting_value:
        :param rule:
        """
        self.setting_name = setting_name
        self.setting_value = setting_value
        self.rule = rule

    def __str__(self):
        return f"{self.setting_name} {self.rule}, not '{self.setting_value}'."
