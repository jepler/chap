# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import sys

import click
import rich

from ..core import get_api, last_session_path, new_session_path
from ..session import Session

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
        self._column = 0
        self._line = ""
        self._sp = ""

    def raw(self, s):
        print(s, end="")

    def add(self, s):
        for line, opt_nl in ipartition(s, "\n"):
            for word, opt_sp in ipartition(line, " "):
                newlen = len(self._line) + len(self._sp) + len(word)
                if not self._line or (newlen <= self._width):
                    self._line += self._sp + word
                    self._sp = opt_sp
                else:
                    if not self._sp and " " in self._line:
                        old_len = len(self._line)
                        self._line, _, partial = self._line.rpartition(" ")
                        print("\r" + self._line + " " * (old_len - len(self._line)))
                        self._line = partial + word
                    else:
                        print()
                        self._line = word
                    self._sp = opt_sp
                print("\r" + self._line, end="")
            if opt_nl:
                print()
                self._line = ""
                self._sp = ""


def verbose_ask(api, session, q, **kw):
    printer = WrappingPrinter()
    tokens = []

    async def work():
        async for token in api.aask(session, q, **kw):
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


@click.command
@click.option("--continue-session", "-s", type=click.Path(exists=True), default=None)
@click.option("--last", is_flag=True)
@click.option("--new-session", "-n", type=click.Path(exists=False), default=None)
@click.option("--system-message", "-S", type=str, default=None)
@click.option("--backend", "-b", type=str, default="openai_chatgpt")
@click.argument("prompt", nargs=-1, required=True)
def main(
    continue_session, last, new_session, system_message, prompt, backend
):  # pylint: disable=too-many-arguments
    """Ask a question (command-line argument is passed as prompt)"""
    if bool(continue_session) + bool(last) + bool(new_session) > 1:
        raise SystemExit(
            "--continue-session, --last and --new_session are mutually exclusive"
        )

    api = get_api(backend)

    if last:
        continue_session = last_session_path()
    if continue_session:
        session_filename = continue_session
        with open(session_filename, "r", encoding="utf-8") as f:
            session = Session.from_json(f.read())  # pylint: disable=no-member
    else:
        session_filename = new_session_path(new_session)
        session = Session.new_session(system_message or api.system_message)

    #    symlink_session_filename(session_filename)

    response = verbose_ask(api, session, " ".join(prompt))

    print(f"Saving session to {session_filename}", file=sys.stderr)
    if response is not None:
        with open(session_filename, "w", encoding="utf-8") as f:
            f.write(session.to_json())


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
