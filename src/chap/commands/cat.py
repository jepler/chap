# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import click

from ..core import last_session_path
from ..session import Session


@click.command
@click.option("--session", "-s", type=click.Path(exists=True), default=None)
@click.option("--last", is_flag=True)
@click.option("--no-system", is_flag=True)
def main(session, last, no_system):
    """Print session in plaintext"""
    if bool(session) + bool(last) != 1:
        raise SystemExit("Specify either --session, or --last")

    if last:
        session = last_session_path()
    with open(session, "r", encoding="utf-8") as f:
        session = Session.from_json(f.read())  # pylint: disable=no-member

    first = True
    for row in session.session:
        if not first:
            print()
        first = False
        if row.role == "user":
            decoration = "**"
        elif row.role == "system":
            if no_system:
                continue
            decoration = "_"
        else:
            decoration = ""

        content = row.content.strip()
        if "\n" in content:
            print(content)
        else:
            print(f"{decoration}{content}{decoration}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
