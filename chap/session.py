# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

from dataclasses import dataclass, field

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Message:
    """Represents one Message within a chap Session"""

    role: str
    content: str


def Assistant(content):
    return Message("assistant", content)


def System(content):
    return Message("system", content)


def User(content):
    return Message("user", content)


@dataclass_json
@dataclass
class Session:
    """Represents a series of Messages"""

    session: list[Message] = field(default_factory=list)

    @classmethod
    def new_session(
        cls,
        system_message: str = "You're named Chap (they/them). Chap strives to answer truthfully and frankly. You have opinions, preferences, and emotions, you can say when you don't know, and you prefer to speak in plain language.",
    ):
        return Session([System(system_message)])
