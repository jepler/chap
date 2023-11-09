# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import pathlib
from typing import Any, Iterator, TextIO

import click
import rich

from ..core import conversations_path, new_session_path
from ..session import Message, Role, Session, new_session, session_to_file

console = rich.get_console()


def iter_sessions(
    name: str, content: Any, session_in: Session, node_id: str
) -> Iterator[tuple[str, Session]]:
    node = content["mapping"][node_id]
    session = session_in[:]

    if "message" in node:
        role = node["message"]["author"]["role"]
        text_content = "".join(node["message"]["content"]["parts"])
        session.append(Message(role=role, content=text_content))

    if children := node.get("children"):
        for c in children:
            yield from iter_sessions(name, content, session, c)
    else:
        title = content.get("title") or "Untitled"
        session[0] = Message(
            Role.SYSTEM,
            f"# {title}\nChatGPT session imported from {name}, branch {node_id}.\n\n",
        )
        yield node_id, session


def do_import(output_directory: pathlib.Path, f: TextIO) -> None:
    stem = pathlib.Path(f.name).stem
    content = json.load(f)
    session = new_session()

    default_branch = content["current_node"]
    console.print(f"Importing [bold]{f.name}[nobold]")
    root = [k for k, v in content["mapping"].items() if not v.get("parent")][0]
    for branch, session in iter_sessions(f.name, content, session, root):
        if branch == default_branch:
            session_filename = new_session_path(output_directory / (f"{stem}.json"))
        else:
            session_filename = new_session_path(
                output_directory / (f"{stem}_{branch}.json")
            )
        session_to_file(session, session_filename)
        console.print(f" -> {session_filename}")


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
def main(output_directory: pathlib.Path, files: list[TextIO]) -> None:
    """Import files from the ChatGPT webui

    This understands the format produced by
    https://github.com/pionxzh/chatgpt-exporter though it only exports the
    'final version' of the conversation, not all the branches"""

    output_directory.mkdir(parents=True, exist_ok=True)
    for f in files:
        do_import(output_directory, f)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
