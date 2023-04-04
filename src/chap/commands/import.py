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


def do_import(output_directory, f):
    content = json.load(f)
    session = Session.new_session(
        f"# {content['title']}\nChatGPT session imported from {f.name}.\n\n**Warning**: only the final conversation branch is imported."
    )
    parts = [content["current_node"]]
    # traverse back from the leaf node to the original conversation node
    for p in parts:
        node = content["mapping"][p]
        parent = node.get("parent")
        if parent is not None:
            parts.append(parent)  # pylint: disable=modified-iterating-list
    # reverse so we get the conversation in chronological order
    for p in reversed(parts):
        node = content["mapping"][p]
        if "message" in node:
            role = node["message"]["author"]["role"]
            text_content = "".join(node["message"]["content"]["parts"])
            session.session.append(Message(role=role, content=text_content))

    # as this includes microseconds, we'll assume it's safe even for a batch import
    session_filename = new_session_path(
        output_directory
        / (datetime.datetime.now().isoformat().replace(":", "_") + ".json")
    )
    with open(session_filename, "w", encoding="utf-8") as f_out:
        f_out.write(session.to_json())  # pylint: disable=no-member
    print(f"imported {f.name} to {session_filename}")


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

    for f in files:
        do_import(output_directory, f)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
