# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import subprocess
import sys

import click
from markdown_it import MarkdownIt
from textual.app import App
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Input, Markdown

from ..core import get_api, last_session_path, new_session_path
from ..session import Assistant, Session, User


def parser_factory():
    parser = MarkdownIt()
    parser.options["html"] = False
    return parser


class Markdown(Markdown, can_focus=True):  # pylint: disable=function-redefined
    pass


def markdown_for_step(step):
    return Markdown(
        step.content.strip() or "…",
        classes="role_" + step.role,
        parser_factory=parser_factory,
    )


class Tui(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        Binding("ctrl+y", "yank", "Yank text", show=True),
        Binding("ctrl+q", "app.quit", "Quit", show=True),
    ]

    def __init__(self, api=None, session=None):
        super().__init__()
        self.api = api or get_api("lorem")
        self.session = session or Session.new_session(self.api.system_message)

    @property
    def input(self):
        return self.query_one(Input)

    @property
    def container(self):
        return self.query_one("#content")

    def compose(self):
        yield Footer()
        yield Input(placeholder="Prompt")
        yield VerticalScroll(Container(id="pad"), id="content")

    async def on_mount(self) -> None:
        await self.container.mount_all(
            [markdown_for_step(step) for step in self.session.session], before="#pad"
        )
        # self.scrollview.scroll_y = self.scrollview.get_content_height()
        self.scroll_end()
        self.input.focus()

    async def on_input_submitted(self, event) -> None:
        self.scroll_end()
        self.input.disabled = True
        output = markdown_for_step(Assistant("*query sent*"))
        await self.container.mount_all(
            [markdown_for_step(User(event.value)), output], before="#pad"
        )
        tokens = []
        update = asyncio.Queue(1)

        async def render_fun():
            while await update.get():
                if tokens:
                    output.update("".join(tokens).strip())
                self.container.scroll_end()
                await asyncio.sleep(0.1)

        async def get_token_fun():
            async for token in self.api.aask(self.session, event.value):
                tokens.append(token)
                try:
                    update.put_nowait(True)
                except asyncio.QueueFull:
                    pass
            await update.put(False)

        try:
            await asyncio.gather(render_fun(), get_token_fun())
            self.input.value = ""
        finally:
            all_output = self.session.session[-1].content
            output.update(all_output)
            output._markdown = all_output  # pylint: disable=protected-access
            self.container.scroll_end()
            self.input.disabled = False

    def scroll_end(self):
        self.call_after_refresh(self.container.scroll_end)

    def action_yank(self):
        widget = self.focused
        if isinstance(widget, Markdown):
            content = widget._markdown  # pylint: disable=protected-access
            subprocess.run(["xsel", "-ib"], input=content.encode("utf-8"), check=False)


@click.command
@click.option("--continue-session", "-s", type=click.Path(exists=True), default=None)
@click.option("--last", is_flag=True)
@click.option("--new-session", "-n", type=click.Path(exists=False), default=None)
@click.option("--system-message", "-S", type=str, default=None)
@click.option("--backend", "-b", type=str, default="openai_chatgpt")
def main(continue_session, last, new_session, system_message, backend):
    """Start interactive terminal user interface session"""
    if bool(continue_session) + bool(last) + bool(new_session) > 1:
        raise SystemExit(
            "--continue-session, --last and --new_session are mutually exclusive"
        )

    api = get_api(backend)

    if last:
        continue_session = last_session_path()
    if continue_session:
        session_filename = continue_session
        with open(session_filename, "r", encoding="utf-8") as f:
            session = Session.from_json(f.read())  # pylint: disable=no-member
    else:
        session_filename = new_session_path(new_session)
        session = Session.new_session(system_message or api.system_message)

    tui = Tui(api, session)
    tui.run()

    sys.stdout.flush()
    sys.stderr.flush()

    print(f"Saving session to {session_filename}", file=sys.stderr)

    with open(session_filename, "w", encoding="utf-8") as f:
        f.write(session.to_json())


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
