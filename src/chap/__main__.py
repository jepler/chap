# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import datetime

import click
import platformdirs

from . import verbose_ask
from .session import Session


def last_session():
    result = max(
        platformdirs.user_cache_path().glob("*.json"), key=lambda p: p.stat().st_mtime
    )
    print(result)
    return result


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
        continue_session = last_session()
    if continue_session:
        session_filename = continue_session
        with open(session_filename, "r", encoding="utf-8") as f:
            session = Session.from_json(f.read())  # pylint: disable=no-member
    else:
        session_filename = new_session or platformdirs.user_cache_path() / (
            datetime.datetime.now().isoformat().replace(":", "_") + ".json"
        )
        print(f"note: Session is in {session_filename}")
        if system_message:
            session = Session.new_session(system_message)
        else:
            session = Session.new_session()

    #    symlink_session_filename(session_filename)

    response = verbose_ask(session, " ".join(prompt))

    if response is not None:
        with open(session_filename, "w", encoding="utf-8") as f:
            f.write(session.to_json())


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
