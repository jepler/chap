# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import datetime
import json
import sys

import httpx
import platformdirs
import rich

from .key import get_key
from .session import Assistant, Message, Session, User

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


def ipartition(s, sep):
    rest = s
    while rest:
        first, opt_sep, rest = rest.partition(sep)
        yield (first, opt_sep)


class WrappingPrinter:
    def __init__(self, width=None):
        self._width = width or rich.get_console().width
        print(f"{self._width=}")
        self._column = 0
        self._line = ""
        self._sp = ""

    def raw(self, s):
        print(s, end="")

    def add(self, s):
        for line, opt_nl in ipartition(s, "\n"):
            for word, opt_sp in ipartition(line, " "):
                newlen = len(self._line) + len(self._sp) + len(word)
                #                print(f"{self._line=} {newlen=}")
                if not self._line or (newlen <= self._width):
                    #                    print(self._line, f"# {len(self._line)} {self._width}")
                    self._line += self._sp + word
                    self._sp = opt_sp
                else:
                    #                    print(self._line, f"# {len(self._line)} {self._width}")
                    if not self._sp and " " in self._line:
                        old_len = len(self._line)
                        self._line, _, partial = self._line.rpartition(" ")
                        print("\r" + self._line + " " * (old_len - len(self._line)))
                        self._line = partial + word
                    else:
                        print()
                        # print(self._line)
                        self._line = word
                    self._sp = opt_sp
                print("\r" + self._line, end="")
            #                print(f"## {self._line=!r}")
            if opt_nl:
                print()
                self._line = ""


#        rest = s
#        while rest:
#            first, nl, rest = s.partition('\n')
#            wrest = first
#            while wrest:
#                word, sp, wrest = wrest.partition(' ')
#                if self._column + len(self._sp) + len(word) > self._width:
#                    print()
#                    self._sp = ''
#                    self._column = 0
#                print(self._sp+word, end='', flush=True)
#                self._column += len(word) + len(self._sp)
#                self._sp = sp
#            if nl:
#                self._sp = ''
#                print()
#                self._column = 0


def verbose_ask(session, q, **kw):
    printer = WrappingPrinter()
    tokens = []

    async def work():
        async for token in aask(session, q, **kw):
            printer.add(token)

    printer.raw(bold)
    printer.add(q)
    printer.raw(nobold)
    printer.add("\n")
    printer.add("\n")
    asyncio.run(work())
    printer.add("\n")
    printer.add("\n")
    result = "".join(tokens)
    return result
