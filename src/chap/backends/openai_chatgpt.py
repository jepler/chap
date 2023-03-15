# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import json

import httpx

from ..key import get_key
from ..session import Assistant, Session, User


class ChatGPT:
    def __init__(self):
        pass

    system_message: str = "You're named Chap (they/them). Chap strives to answer truthfully and frankly. You have opinions, preferences, and emotions, you can say when you don't know, and you prefer to speak in plain language."

    def ask(self, session, query, *, max_query_size=5, timeout=60):
        full_prompt = Session(session.session + [User(query)])
        del full_prompt.session[1:-max_query_size]

        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
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

    async def aask(self, session, query, *, max_query_size=5, timeout=60):
        full_prompt = Session(session.session + [User(query)])
        del full_prompt.session[1:-max_query_size]

        new_content = []
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers={"authorization": f"Bearer {self.get_key()}"},
                    json={
                        "model": "gpt-3.5-turbo",
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
    return ChatGPT()
