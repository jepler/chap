import functools
import os
import platformdirs

class NoKeyAvailable(Exception):
    pass

_key_path = platformdirs.user_config_path('chap')/'openai_api_key'

@functools.cache
def get_key():
    if not _key_path.exists():
        raise NoKeyAvailable(f"Place your openai api key in {_key_path} and run the program again")

    with open(_key_path) as f:
        return f.read().strip()
