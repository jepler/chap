# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import functools
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


@functools.lru_cache()
def _get_tokenizer(model_name):
    import transformers  # pylint: disable=import-outside-toplevel

    return transformers.AutoTokenizer.from_pretrained(model_name)


@functools.lru_cache()
def supports_system_message(model_name):
    import jinja2.exceptions  # pylint: disable=import-outside-toplevel

    tokenizer = _get_tokenizer(model_name)
    try:
        tokenizer.apply_chat_template(
            [{"role": "system", "content": "lorem"}], tokenize=False
        )
        return True
    except jinja2.exceptions.TemplateError:
        return False


def fix_system_message(model_name, messages):
    if supports_system_message(model_name):
        return messages
    if not messages:
        return messages
    if messages[0].role != "system":
        return messages

    system_message = messages[0]
    if len(messages) > 1:
        messages = [
            User(f"{system_message.content}\n\n{messages[1].content}")
        ] + messages[2:]
    else:
        messages = [User(system_message.content)]

    return messages


def apply_chat_template(model_name, messages, tokenize):
    messages = fix_system_message(model_name, messages)
    tokenizer = _get_tokenizer(model_name)
    print(messages)
    return tokenizer.apply_chat_template(messages, tokenize=tokenize)


def count_tokens(model_name, messages):
    return len(apply_chat_template(model_name, messages, True))


def get_prompt(model_name, messages, approx_max_tokens):
    if not messages:
        return ""
    remaining_tokens = approx_max_tokens
    if messages and messages[0].role == "system":
        system_prompt = messages[0]
        messages = messages[1:]
        remaining_tokens -= count_tokens(model_name, [system_prompt])
    else:
        remaining_tokens = approx_max_tokens
        system_prompt = None
    parts = []
    for i in range(len(messages) - 1, -1, -2):
        tokens = count_tokens(model_name, messages[i : i + 2])
        remaining_tokens -= tokens
        if remaining_tokens < 0:
            break
        parts.extend(messages[i : i + 2][::-1])
    parts = parts[::-1]
    if system_prompt:
        parts.insert(0, system_prompt)
    return apply_chat_template(model_name, parts, tokenize=False)
