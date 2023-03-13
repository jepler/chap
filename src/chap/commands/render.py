# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import click
import rich
from rich.markdown import Markdown

from ..core import last_session_path
from ..session import Session


@click.command
@click.option("--session", "-s", type=click.Path(exists=True), default=None)
@click.option("--last", is_flag=True)
def main(session, last):
    if bool(session) + bool(last) != 1:
        raise SystemExit("Specify either --session, or --last")

    if last:
        session = last_session_path()
    with open(session, "r", encoding="utf-8") as f:
        session = Session.from_json(f.read())  # pylint: disable=no-member

    console = rich.get_console()
    first = True
    for row in session.session:
        if not first:
            console.print()
        first = False
        content = row.content
        role = row.role
        if role == "user":
            style = "bold"
        elif role == "system":
            style = "italic"
        else:
            style = "none"
        console.print(Markdown(content, style=style))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
