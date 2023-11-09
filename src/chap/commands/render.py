# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import click
import rich
from markdown_it import MarkdownIt
from rich.markdown import Markdown

from ..core import command_uses_existing_session
from ..session import Role


def to_markdown(message):
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
def main(obj, no_system):
    """Print session with formatting"""
    session = obj.session

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
