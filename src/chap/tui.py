# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import datetime
import subprocess

import click
import platformdirs
from textual.app import App
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Input, MarkdownViewer

from . import Assistant, User, aask
from .session import Session


def last_session():
    result = max(
        platformdirs.user_cache_path().glob("*.json"), key=lambda p: p.stat().st_mtime
    )
    print(result)
    return result


def markdown_for_step(step):
    return MarkdownViewer(
        step.content.strip(), classes="role_" + step.role, show_table_of_contents=False
    )


class Tui(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        Binding("ctrl+y", "yank", "Yank text", show=True),
        Binding("ctrl+c,ctrl+q", "app.quit", "Quit", show=True),
    ]

    def __init__(self, session):
        super().__init__()
        self.session = session

    @property
    def input(self):
        return self.query_one(Input)

    @property
    def container(self):
        return self.query_one(Container)

    def compose(self):
        yield Footer()
        yield Input(placeholder="Prompt")
        yield Container()

    async def on_mount(self) -> None:
        self.container.mount_all(
            [markdown_for_step(step) for step in self.session.session]
        )
        # self.scrollview.scroll_y = self.scrollview.get_content_height()
        self.scroll_end()
        self.input.focus()

    async def on_input_submitted(self, event) -> None:
        self.scroll_end()
        self.input.disabled = True
        self.container.mount_all(
            [
                markdown_for_step(User(event.value)),
                output := markdown_for_step(Assistant("*query sent*")),
            ]
        )
        tokens = []
        try:
            async for token in aask(self.session, event.value):
                tokens.append(token)
                await output.document.update("".join(tokens))
                self.container.scroll_end()
            self.input.value = ""
        finally:
            output._markdown = "".join(tokens)  # pylint: disable=protected-access
            self.input.disabled = False

    def scroll_end(self):
        self.call_after_refresh(self.container.scroll_end)

    def action_yank(self):
        widget = self.focused
        if isinstance(widget, MarkdownViewer):
            content = widget._markdown  # pylint: disable=protected-access
            subprocess.run(["xsel", "-ib"], input=content.encode("utf-8"), check=False)


@click.command
@click.option("--continue-session", "-s", type=click.Path(exists=True), default=None)
@click.option("--last", is_flag=True)
@click.option("--new-session", "-n", type=click.Path(exists=False), default=None)
@click.option("--system-message", "-S", type=str, default=None)
def main(continue_session, last, new_session, system_message):
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

    tui = Tui(session)
    tui.run()

    print("saving session")
    with open(session_filename, "w", encoding="utf-8") as f:
        f.write(session.to_json())


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
