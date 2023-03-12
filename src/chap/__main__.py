# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import sys

import click

from . import last_session_path, new_session_path, verbose_ask
from .session import Session


@click.command
@click.option("--continue-session", "-s", type=click.Path(exists=True), default=None)
@click.option("--last", is_flag=True)
@click.option("--new-session", "-n", type=click.Path(exists=False), default=None)
@click.option("--system-message", "-S", type=str, default=None)
@click.argument("prompt", nargs=-1, required=True)
def main(continue_session, last, new_session, system_message, prompt):
    if bool(continue_session) + bool(last) + bool(new_session) > 1:
        raise SystemExit(
            "--continue-session, --last and --new_session are mutually exclusive"
        )

    if last:
        continue_session = last_session_path()
    if continue_session:
        session_filename = continue_session
        with open(session_filename, "r", encoding="utf-8") as f:
            session = Session.from_json(f.read())  # pylint: disable=no-member
    else:
        session_filename = new_session_path(new_session)
        if system_message:
            session = Session.new_session(system_message)
        else:
            session = Session.new_session()

    #    symlink_session_filename(session_filename)

    response = verbose_ask(session, " ".join(prompt))

    print(f"Saving session to {session_filename}", file=sys.stderr)
    if response is not None:
        with open(session_filename, "w", encoding="utf-8") as f:
            f.write(session.to_json())


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
