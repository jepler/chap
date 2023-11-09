# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass
from typing import cast

from typing_extensions import TypedDict


# not an enum.Enum because these objects are not json-serializable, sigh
class Role:  # pylint: disable=too-few-public-methods
    ASSISTANT = "assistant"
    SYSTEM = "system"
    USER = "user"


@dataclass
class Message:
    """Represents one Message within a chap Session"""

    role: str
    content: str


MessageDict = TypedDict("MessageDict", {"role": str, "content": int})
Session = list[Message]
SessionDicts = list[MessageDict]


def Assistant(content: str) -> Message:
    return Message(Role.ASSISTANT, content)


def System(content: str) -> Message:
    return Message(Role.SYSTEM, content)


def User(content: str) -> Message:
    return Message(Role.USER, content)


def new_session(
    system_message: str = "You're named Chap (they/them). Chap strives to answer truthfully and frankly. You have opinions, preferences, and emotions, you can say when you don't know, and you prefer to speak in plain language.",
) -> Session:
    return [System(system_message)]


def session_to_json(session: Session) -> str:
    return json.dumps(session_to_list(session))


def session_to_list(session: Session) -> SessionDicts:
    return [cast(MessageDict, asdict(message)) for message in session]


def session_from_json(data: str) -> Session:
    j = json.loads(data)
    if isinstance(j, dict):
        j = j["session"]
    return [Message(**mapping) for mapping in j]


def session_from_file(path: pathlib.Path | str) -> Session:
    with open(path, "r", encoding="utf-8") as f:
        return session_from_json(f.read())


def session_to_file(session: Session, path: pathlib.Path | str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(session_to_json(session))
