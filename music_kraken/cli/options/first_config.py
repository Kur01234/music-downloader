from .frontend import set_frontend


def initial_config():
    code = set_frontend(no_cli=True)
    return code
