# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import subprocess
import sys

from markdown_it import MarkdownIt
from textual import work
from textual.app import App
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Input, LoadingIndicator, Markdown

from ..core import command_uses_new_session, get_api, new_session_path
from ..session import Assistant, Session, User


def parser_factory():
    parser = MarkdownIt()
    parser.options["html"] = False
    return parser


class Markdown(
    Markdown, can_focus=True, can_focus_children=False
):  # pylint: disable=function-redefined
    BINDINGS = [
        Binding("ctrl+y", "yank", "Yank text", show=True),
        Binding("ctrl+r", "resubmit", "resubmit", show=True),
        Binding("ctrl+x", "redraft", "redraft", show=True),
        Binding("ctrl+q", "toggle_history", "history toggle", show=True),
    ]


def markdown_for_step(step):
    return Markdown(
        step.content.strip() or "…",
        classes="role_" + step.role,
        parser_factory=parser_factory,
    )


class CancelButton(Button):
    BINDINGS = [
        Binding("escape", "stop_generating", "Stop Generating", show=True),
    ]


class Tui(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
    ]

    def __init__(self, api=None, session=None):
        super().__init__()
        self.api = api or get_api("lorem")
        self.session = session or Session.new_session(self.api.system_message)

    @property
    def spinner(self):
        return self.query_one(LoadingIndicator)

    @property
    def wait(self):
        return self.query_one("#wait")

    @property
    def input(self):
        return self.query_one(Input)

    @property
    def cancel_button(self):
        return self.query_one(CancelButton)

    @property
    def container(self):
        return self.query_one("#content")

    def compose(self):
        yield Footer()
        yield VerticalScroll(
            *[markdown_for_step(step) for step in self.session.session],
            # The pad container helps reduce flickering when rendering fresh
            # content and scrolling. (it's not clear why this makes a
            # difference and it'd be nice to be rid of the workaround)
            Container(id="pad"),
            id="content",
        )
        yield Input(placeholder="Prompt")
        with Horizontal(id="wait"):
            yield LoadingIndicator()
            yield CancelButton(label="❌ Stop Generation", id="cancel", disabled=True)

    async def on_mount(self) -> None:
        self.container.scroll_end(animate=False)
        self.input.focus()

    async def on_input_submitted(self, event) -> None:
        self.get_completion(event.value)

    @work(exclusive=True)
    async def get_completion(self, query):
        self.scroll_end()

        self.input.styles.display = "none"
        self.wait.styles.display = "block"
        self.input.disabled = True
        self.cancel_button.disabled = False

        self.cancel_button.focus()
        output = markdown_for_step(Assistant("*query sent*"))
        await self.container.mount_all(
            [markdown_for_step(User(query)), output], before="#pad"
        )
        tokens = []
        update = asyncio.Queue(1)

        for markdown in self.container.children:
            markdown.disabled = True

        # Construct a fake session with only select items
        session = Session()
        for si, wi in zip(self.session.session, self.container.children):
            if not wi.has_class("history_exclude"):
                session.session.append(si)

        message = Assistant("")
        self.session.session.extend(
            [
                User(query),
                message,
            ]
        )

        async def render_fun():
            while await update.get():
                if tokens:
                    output.update("".join(tokens).strip())
                self.container.scroll_end()
                await asyncio.sleep(0.1)

        async def get_token_fun():
            async for token in self.api.aask(session, query):
                tokens.append(token)
                message.content += token
                try:
                    update.put_nowait(True)
                except asyncio.QueueFull:
                    # QueueFull exception is expected. If something's in the
                    # queue then render_fun will run soon.
                    pass
            await update.put(False)

        try:
            await asyncio.gather(render_fun(), get_token_fun())
        finally:
            self.input.value = ""
            all_output = self.session.session[-1].content
            output.update(all_output)
            output._markdown = all_output  # pylint: disable=protected-access
            self.container.scroll_end()

            for markdown in self.container.children:
                markdown.disabled = False

            self.input.styles.display = "block"
            self.wait.styles.display = "none"
            self.input.disabled = False
            self.cancel_button.disabled = True
            self.input.focus()

    def scroll_end(self):
        self.call_after_refresh(self.container.scroll_end)

    def action_yank(self):
        widget = self.focused
        if isinstance(widget, Markdown):
            content = widget._markdown  # pylint: disable=protected-access
            subprocess.run(["xsel", "-ib"], input=content.encode("utf-8"), check=False)

    def action_toggle_history(self):
        widget = self.focused
        if not isinstance(widget, Markdown):
            return
        children = self.container.children
        idx = children.index(widget)
        while idx > 1 and not "role_user" in children[idx].classes:
            idx -= 1
        widget = children[idx]

        children[idx].toggle_class("history_exclude")
        children[idx + 1].toggle_class("history_exclude")

    async def action_stop_generating(self):
        self.workers.cancel_all()

    async def on_button_pressed(self, event):  # pylint: disable=unused-argument
        self.workers.cancel_all()

    async def action_quit(self):
        self.workers.cancel_all()
        self.exit()

    async def action_resubmit(self):
        await self.redraft_or_resubmit(True)

    async def action_redraft(self):
        await self.redraft_or_resubmit(False)

    async def redraft_or_resubmit(self, resubmit):
        widget = self.focused
        if not isinstance(widget, Markdown):
            return
        children = self.container.children
        idx = children.index(widget)
        while idx > 1 and not children[idx].has_class("role_user"):
            idx -= 1
        widget = children[idx]

        # Save a copy of the discussion before this deletion
        with open(new_session_path(), "w", encoding="utf-8") as f:
            f.write(self.session.to_json())

        query = self.session.session[idx].content
        self.input.value = query

        del self.session.session[idx:]
        for child in self.container.children[idx:-1]:
            await child.remove()

        self.input.focus()
        if resubmit:
            await self.input.action_submit()


@command_uses_new_session
def main(obj):
    """Start interactive terminal user interface session"""
    api = obj.api
    session = obj.session
    session_filename = obj.session_filename

    tui = Tui(api, session)
    tui.run()

    sys.stdout.flush()
    sys.stderr.flush()

    print(f"Saving session to {session_filename}", file=sys.stderr)

    with open(session_filename, "w", encoding="utf-8") as f:
        f.write(session.to_json())


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
