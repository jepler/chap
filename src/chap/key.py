# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import json
import subprocess
from typing import Protocol
import functools

import platformdirs


class APIKeyProtocol(Protocol):
    @property
    def api_key_name(self) -> str:
        ...


class HasKeyProtocol(Protocol):
    @property
    def parameters(self) -> APIKeyProtocol:
        ...


class UsesKeyMixin:
    def get_key(self: HasKeyProtocol) -> str:
        return get_key(self.parameters.api_key_name)


class NoKeyAvailable(Exception):
    pass


_key_path_base = platformdirs.user_config_path("chap")

USE_PASSWORD_STORE = _key_path_base / "USE_PASSWORD_STORE"

if USE_PASSWORD_STORE.exists():
    content = USE_PASSWORD_STORE.read_text(encoding="utf-8")
    if content.strip():
        cfg = json.loads(content)
    pass_command: list[str] = cfg.get("PASS_COMMAND", ["pass", "show"])
    pass_prefix: str = cfg.get("PASS_PREFIX", "chap/")

    @functools.cache
    def get_key(name: str, what: str = "api key") -> str:
        key_path = f"{pass_prefix}{name}"
        command = pass_command + [key_path]
        return subprocess.check_output(command, encoding="utf-8").split("\n")[0]

else:

    @functools.cache
    def get_key(name: str, what: str = "api key") -> str:
        key_path = _key_path_base / name
        if not key_path.exists():
            raise NoKeyAvailable(
                f"Place your {what} in {key_path} and run the program again"
            )

        with open(key_path, encoding="utf-8") as f:
            return f.read().strip()
