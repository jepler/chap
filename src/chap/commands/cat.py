# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import click

from ..core import Obj, command_uses_existing_session
from ..session import Role


@command_uses_existing_session
@click.option("--no-system", is_flag=True)
def main(obj: Obj, no_system: bool) -> None:
    """Print session in plaintext"""
    session = obj.session
    if not session:
        return

    first = True
    for row in session:
        if not first:
            print()
        first = False
        if row.role == Role.USER:
            decoration = "**"
        elif row.role == Role.SYSTEM:
            if no_system:
                continue
            decoration = "_"
        else:
            decoration = ""

        content = str(row.content).strip()
        if "\n" in content:
            print(content)
        else:
            print(f"{decoration}{content}{decoration}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
