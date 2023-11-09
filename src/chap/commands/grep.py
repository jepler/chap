# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pathlib
import re
import sys
from typing import Iterable, Optional, Tuple

import click
import rich

from ..core import conversations_path as default_conversations_path
from ..session import Message, session_from_file
from .render import to_markdown


def list_files_matching_rx(
    rx: re.Pattern[str], conversations_path: Optional[pathlib.Path] = None
) -> Iterable[Tuple[pathlib.Path, Message]]:
    for conversation in (conversations_path or default_conversations_path).glob(
        "*.json"
    ):
        try:
            session = session_from_file(conversation)  # pylint: disable=no-member
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Failed to read {conversation}: {e}", file=sys.stderr)
            continue

        for message in session:
            if isinstance(message.content, str) and rx.search(message.content):
                yield conversation, message


@click.command
@click.option("--ignore-case", "-i", is_flag=True)
@click.option("--files-with-matches", "-l", is_flag=True)
@click.option("--fixed-strings", "--literal", "-F", is_flag=True)
@click.argument("pattern", nargs=1, required=True)
def main(
    ignore_case: bool, files_with_matches: bool, fixed_strings: bool, pattern: str
) -> None:
    """Search sessions for pattern"""
    console = rich.get_console()
    if fixed_strings:
        pattern = re.escape(pattern)

    rx = re.compile(pattern, re.I if ignore_case else 0)
    last_file = None
    for f, m in list_files_matching_rx(rx, None):
        if f != last_file:
            if files_with_matches:
                print(f)
            else:
                if last_file:
                    print()
                console.print(f"[bold]{f}[nobold]:")
            last_file = f
        else:
            if not files_with_matches:
                console.print("[dim]---[nodim]")
        if not files_with_matches:
            m.content, _ = rx.subn(lambda p: f"**{p.group(0)}**", m.content)
            console.print(to_markdown(m))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
