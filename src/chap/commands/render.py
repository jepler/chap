# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import click
import rich
from markdown_it import MarkdownIt
from rich.markdown import Markdown

from ..core import Obj, command_uses_existing_session
from ..session import Message, Role


def to_markdown(message: Message) -> Markdown:
    role = message.role
    if role == Role.USER:
        style = "bold"
    elif role == Role.SYSTEM:
        style = "italic"
    else:
        style = "none"
    m = Markdown("", style=style)
    parser = MarkdownIt()
    parser.options["html"] = False
    m.parsed = parser.parse(str(message.content).strip())
    return m


@command_uses_existing_session
@click.option("--no-system", is_flag=True)
def main(obj: Obj, no_system: bool) -> None:
    """Print session with formatting"""
    session = obj.session
    assert session is not None

    console = rich.get_console()
    first = True
    for row in session:
        if not first:
            console.print()
        first = False
        if no_system and row.role == Role.SYSTEM:
            continue
        console.print(to_markdown(row))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
