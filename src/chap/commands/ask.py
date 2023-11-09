# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import sys
from typing import Iterable, Protocol

import click
import rich

from ..core import Backend, Obj, command_uses_new_session
from ..session import Session, session_to_file

bold = "\033[1m"
nobold = "\033[m"


def ipartition(s: str, sep: str) -> Iterable[tuple[str, str]]:
    rest = s
    while rest:
        first, opt_sep, rest = rest.partition(sep)
        yield (first, opt_sep)


class Printable(Protocol):
    def raw(self, s: str) -> None:
        """Print a raw escape code"""

    def add(self, s: str) -> None:
        """Add text to the output"""


class DumbPrinter:
    def raw(self, s: str) -> None:
        pass

    def add(self, s: str) -> None:
        print(s, end="")


class WrappingPrinter:
    def __init__(self, width: int | None = None) -> None:
        self._width = width or rich.get_console().width
        self._column = 0
        self._line = ""
        self._sp = ""

    def raw(self, s: str) -> None:
        print(s, end="")

    def add(self, s: str) -> None:
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


def verbose_ask(api: Backend, session: Session, q: str, print_prompt: bool) -> str:
    printer: Printable
    if sys.stdout.isatty():
        printer = WrappingPrinter()
    else:
        printer = DumbPrinter()
    tokens: list[str] = []

    async def work() -> None:
        async for token in api.aask(session, q):
            printer.add(token)

    if print_prompt:
        printer.raw(bold)
        printer.add(q)
        printer.raw(nobold)
        printer.add("\n")
        printer.add("\n")

    asyncio.run(work())
    printer.add("\n")
    result = "".join(tokens)
    return result


@command_uses_new_session
@click.option("--print-prompt/--no-print-prompt", default=True)
@click.argument("prompt", nargs=-1, required=True)
def main(obj: Obj, prompt: str, print_prompt: bool) -> None:
    """Ask a question (command-line argument is passed as prompt)"""
    session = obj.session
    assert session is not None

    session_filename = obj.session_filename
    assert session_filename is not None

    api = obj.api
    assert api is not None

    #    symlink_session_filename(session_filename)

    response = verbose_ask(api, session, " ".join(prompt), print_prompt=print_prompt)

    print(f"Saving session to {session_filename}", file=sys.stderr)
    if response is not None:
        session_to_file(session, session_filename)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
