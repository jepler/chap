# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

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


@functools.cache
def get_key(name: str, what: str = "openai api key") -> str:
    key_path = _key_path_base / name
    if not key_path.exists():
        raise NoKeyAvailable(
            f"Place your {what} in {key_path} and run the program again"
        )

    with open(key_path, encoding="utf-8") as f:
        return f.read().strip()
