# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import datetime
import json
import pathlib

import click

from ..core import conversations_path, new_session_path
from ..session import Message, Session


def iter_sessions(name, content, session_in, node_id):
    node = content["mapping"][node_id]
    session = Session(session_in.session[:])

    if "message" in node:
        role = node["message"]["author"]["role"]
        text_content = "".join(node["message"]["content"]["parts"])
        session.session.append(Message(role=role, content=text_content))

    if children := node.get("children"):
        for c in children:
            yield from iter_sessions(name, content, session, c)
    else:
        title = content.get("title") or "Untitled"
        session.session[0] = Message(
            "system",
            f"# {title}\nChatGPT session imported from {name}, branch {node_id}.\n\n",
        )
        yield node_id, session


def do_import(output_directory, f):
    content = json.load(f)
    session = Session.new_session()

    root = [k for k, v in content["mapping"].items() if not v.get("parent")][0]
    for branch, session in iter_sessions(f.name, content, session, root):
        # as this includes microseconds, we'll assume it's safe even for a batch import
        session_filename = new_session_path(
            output_directory
            / (datetime.datetime.now().isoformat().replace(":", "_") + ".json")
        )
        with open(session_filename, "w", encoding="utf-8") as f_out:
            f_out.write(session.to_json())  # pylint: disable=no-member
        print(f"imported {f.name} branch {branch} to {session_filename}")


@click.command
@click.option(
    "--output-directory",
    "-o",
    type=click.Path(file_okay=False, path_type=pathlib.Path),
    default=conversations_path,
)
@click.argument(
    "files", nargs=-1, required=True, type=click.File("r", encoding="utf-8")
)
def main(output_directory, files):
    """Import files from the ChatGPT webui

    This understands the format produced by
    https://github.com/pionxzh/chatgpt-exporter though it only exports the
    'final version' of the conversation, not all the branches"""

    output_directory.mkdir(parents=True, exist_ok=True)
    for f in files:
        do_import(output_directory, f)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
