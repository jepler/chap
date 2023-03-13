# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import datetime
import importlib

import platformdirs

conversations_path = platformdirs.user_state_path("chap") / "conversations"
conversations_path.mkdir(parents=True, exist_ok=True)


def last_session_path():
    result = max(
        conversations_path.glob("*.json"), key=lambda p: p.stat().st_mtime, default=None
    )
    print(result)
    return result


def new_session_path(opt_path=None):
    return opt_path or conversations_path / (
        datetime.datetime.now().isoformat().replace(":", "_") + ".json"
    )


def get_api(name="openai_chatgpt"):
    return importlib.import_module(f"{__package__}.backends.{name}").factory()


def ask(*args, **kw):
    return get_api().ask(*args, **kw)


def aask(*args, **kw):
    return get_api().aask(*args, **kw)
