# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import functools
import json
from dataclasses import dataclass

import httpx
import tiktoken

from ..key import get_key
from ..session import Assistant, Session, User


@dataclass(frozen=True)
class EncodingMeta:
    encoding: tiktoken.Encoding
    tokens_per_message: int
    tokens_per_name: int

    @functools.lru_cache()
    def encode(self, s):
        return self.encoding.encode(s)

    def num_tokens_for_message(self, message):
        # n.b. chap doesn't use message.name yet
        return len(self.encode(message.role)) + len(self.encode(message.content))

    def num_tokens_for_messages(self, messages):
        return sum(self.num_tokens_for_message(message) for message in messages) + 3

    @classmethod
    @functools.cache
    def from_model(cls, model):
        if model == "gpt-3.5-turbo":
            # print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
            model = "gpt-3.5-turbo-0613"
        if model == "gpt-4":
            # print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
            model = "gpt-4-0613"

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            print("Warning: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")

        if model in {
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k-0613",
            "gpt-4-0314",
            "gpt-4-32k-0314",
            "gpt-4-0613",
            "gpt-4-32k-0613",
        }:
            tokens_per_message = 3
            tokens_per_name = 1
        elif model == "gpt-3.5-turbo-0301":
            tokens_per_message = (
                4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            )
            tokens_per_name = -1  # if there's a name, the role is omitted
        else:
            raise NotImplementedError(
                f"""EncodingMeta is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
            )
        return cls(encoding, tokens_per_message, tokens_per_name)


class ChatGPT:
    @dataclass
    class Parameters:
        model: str = "gpt-3.5-turbo"
        """The model to use. The most common alternative value is 'gpt-4'."""

        max_request_tokens: int = 1024
        """The approximate greatest number of tokens to send in a request. When the session is long, the system prompt and 1 or more of the most recent interaction steps are sent."""

    def __init__(self):
        self.parameters = self.Parameters()

    system_message: str = "You're named Chap (they/them). Chap strives to answer truthfully and frankly. You have opinions, preferences, and emotions, you can say when you don't know, and you prefer to speak in plain language."

    def make_full_prompt(self, all_history):
        encoding = EncodingMeta.from_model(self.parameters.model)
        result = [all_history[0]]  # Assumed to be system prompt
        left = self.parameters.max_request_tokens - encoding.num_tokens_for_messages(
            result
        )
        parts = []
        for message in reversed(all_history[1:]):
            msglen = encoding.num_tokens_for_message(message)
            if left >= msglen:
                left -= msglen
                parts.append(message)
            else:
                break
        result.extend(reversed(parts))
        return Session(result)

    def ask(self, session, query, *, timeout=60):
        full_prompt = self.make_full_prompt(session.session + [User(query)])
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": self.parameters.model,
                "messages": full_prompt.to_dict()[  # pylint: disable=no-member
                    "session"
                ],
            },  # pylint: disable=no-member
            headers={
                "Authorization": f"Bearer {self.get_key()}",
            },
            timeout=timeout,
        )
        if response.status_code != 200:
            print("Failure", response.status_code, response.text)
            return None

        try:
            j = response.json()
            result = j["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.decoder.JSONDecodeError):
            print("Failure", response.status_code, response.text)
            return None

        session.session.extend([User(query), Assistant(result)])
        return result

    async def aask(self, session, query, *, timeout=60):
        full_prompt = self.make_full_prompt(session.session + [User(query)])
        new_content = []
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers={"authorization": f"Bearer {self.get_key()}"},
                    json={
                        "model": self.parameters.model,
                        "stream": True,
                        "messages": full_prompt.to_dict()[  # pylint: disable=no-member
                            "session"
                        ],  # pylint: disable=no-member
                    },
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data:"):
                                data = line.removeprefix("data:").strip()
                                if data == "[DONE]":
                                    break
                                j = json.loads(data)
                                delta = j["choices"][0]["delta"]
                                content = delta.get("content")
                                if content:
                                    new_content.append(content)
                                    yield content
                    else:
                        content = f"\nFailed with {response=!r}"
                        new_content.append(content)
                        yield content

        except httpx.HTTPError as e:
            content = f"\nException: {e!r}"
            new_content.append(content)
            yield content

        session.session.extend([User(query), Assistant("".join(new_content))])

    @classmethod
    def get_key(cls):
        return get_key("openai_api_key")


def factory():
    """Uses the OpenAI chat completion API"""
    return ChatGPT()
