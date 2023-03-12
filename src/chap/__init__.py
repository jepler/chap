# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import json
import sys

import httpx

from .key import get_key
from .session import Assistant, Message, Session, User


def ask(session, query, *, max_query_size=5, timeout=60):
    full_prompt = Session(session.session + [User(query)])
    del full_prompt.session[1:-max_query_size]

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        json={
            "model": "gpt-3.5-turbo",
            "messages": full_prompt.to_dict()["session"],  # pylint: disable=no-member
        },  # pylint: disable=no-member
        headers={
            "Authorization": f"Bearer {get_key()}",
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


async def aask(session, query, *, max_query_size=5):
    full_prompt = Session(session.session + [User(query)])
    del full_prompt.session[1:-max_query_size]

    new_content = []
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={"authorization": f"Bearer {get_key()}"},
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
                yield f"Failed with {response.status_code}"
                return

    session.session.extend([User(query), Assistant("".join(new_content))])


if sys.stdout.isatty():
    bold = "\033[1m"
    nobold = "\033[m"
else:
    bold = nobold = ""


def verbose_ask(session, q, **kw):
    print(f"{bold}{q}{nobold}")
    print()
    print(result := ask(session, q, **kw))
    print()
    return result
