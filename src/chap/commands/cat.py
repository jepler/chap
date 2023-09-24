# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import click

from ..core import command_uses_existing_session


@command_uses_existing_session
@click.option("--no-system", is_flag=True)
def main(obj, no_system):
    """Print session in plaintext"""
    session = obj.session

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

        content = str(row.content).strip()
        if "\n" in content:
            print(content)
        else:
            print(f"{decoration}{content}{decoration}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
