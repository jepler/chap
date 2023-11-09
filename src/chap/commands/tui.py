# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import subprocess
import sys
from typing import cast

from markdown_it import MarkdownIt
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Input, LoadingIndicator, Markdown

from ..core import Backend, Obj, command_uses_new_session, get_api, new_session_path
from ..session import Assistant, Message, Session, User, new_session, session_to_file


def parser_factory() -> MarkdownIt:
    parser = MarkdownIt()
    parser.options["html"] = False
    return parser


class ChapMarkdown(
    Markdown, can_focus=True, can_focus_children=False
):  # pylint: disable=function-redefined
    BINDINGS = [
        Binding("ctrl+y", "yank", "Yank text", show=True),
        Binding("ctrl+r", "resubmit", "resubmit", show=True),
        Binding("ctrl+x", "redraft", "redraft", show=True),
        Binding("ctrl+q", "toggle_history", "history toggle", show=True),
    ]


def markdown_for_step(step: Message) -> ChapMarkdown:
    return ChapMarkdown(
        step.content.strip() or "…",
        classes="role_" + step.role,
        parser_factory=parser_factory,
    )


class CancelButton(Button):
    BINDINGS = [
        Binding("escape", "stop_generating", "Stop Generating", show=True),
    ]


class Tui(App[None]):
    CSS_PATH = "tui.css"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
    ]

    def __init__(
        self, api: Backend | None = None, session: Session | None = None
    ) -> None:
        super().__init__()
        self.api = api or get_api("lorem")
        self.session = (
            new_session(self.api.system_message) if session is None else session
        )

    @property
    def spinner(self) -> LoadingIndicator:
        return self.query_one(LoadingIndicator)

    @property
    def wait(self) -> VerticalScroll:
        return cast(VerticalScroll, self.query_one("#wait"))

    @property
    def input(self) -> Input:
        return self.query_one(Input)

    @property
    def cancel_button(self) -> CancelButton:
        return self.query_one(CancelButton)

    @property
    def container(self) -> VerticalScroll:
        return cast(VerticalScroll, self.query_one("#content"))

    def compose(self) -> ComposeResult:
        yield Footer()
        yield VerticalScroll(
            *[markdown_for_step(step) for step in self.session],
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

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        self.get_completion(event.value)

    @work(exclusive=True)
    async def get_completion(self, query: str) -> None:
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
        tokens: list[str] = []
        update: asyncio.Queue[bool] = asyncio.Queue(1)

        for markdown in self.container.children:
            markdown.disabled = True

        # Construct a fake session with only select items
        session = []
        for si, wi in zip(self.session, self.container.children):
            if not wi.has_class("history_exclude"):
                session.append(si)

        message = Assistant("")
        self.session.extend(
            [
                User(query),
                message,
            ]
        )

        async def render_fun() -> None:
            while await update.get():
                if tokens:
                    output.update("".join(tokens).strip())
                self.container.scroll_end()
                await asyncio.sleep(0.1)

        async def get_token_fun() -> None:
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
            all_output = self.session[-1].content
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

    def scroll_end(self) -> None:
        self.call_after_refresh(self.container.scroll_end)

    def action_yank(self) -> None:
        widget = self.focused
        if isinstance(widget, ChapMarkdown):
            content = widget._markdown or ""  # pylint: disable=protected-access
            subprocess.run(["xsel", "-ib"], input=content.encode("utf-8"), check=False)

    def action_toggle_history(self) -> None:
        widget = self.focused
        if not isinstance(widget, ChapMarkdown):
            return
        children = self.container.children
        idx = children.index(widget)
        if idx == 0:
            return

        while idx > 1 and not children[idx].has_class("role_user"):
            idx -= 1

        for m in children[idx : idx + 2]:
            m.toggle_class("history_exclude")

    async def action_stop_generating(self) -> None:
        self.workers.cancel_all()

    async def on_button_pressed(  # pylint: disable=unused-argument
        self, event: Button.Pressed
    ) -> None:
        self.workers.cancel_all()

    async def action_quit(self) -> None:
        self.workers.cancel_all()
        self.exit()

    async def action_resubmit(self) -> None:
        await self.redraft_or_resubmit(True)

    async def action_redraft(self) -> None:
        await self.redraft_or_resubmit(False)

    async def redraft_or_resubmit(self, resubmit: bool) -> None:
        widget = self.focused
        if not isinstance(widget, ChapMarkdown):
            return
        children = self.container.children
        idx = children.index(widget)
        if idx < 1:
            return

        while idx > 1 and not children[idx].has_class("role_user"):
            idx -= 1

        # Save a copy of the discussion before this deletion
        session_to_file(self.session, new_session_path())

        query = self.session[idx].content
        self.input.value = query

        del self.session[idx:]
        for child in self.container.children[idx:-1]:
            await child.remove()

        self.input.focus()
        if resubmit:
            await self.input.action_submit()


@command_uses_new_session
def main(obj: Obj) -> None:
    """Start interactive terminal user interface session"""
    api = obj.api
    assert api is not None
    session = obj.session
    assert session is not None
    session_filename = obj.session_filename
    assert session_filename is not None

    tui = Tui(api, session)
    tui.run()

    sys.stdout.flush()
    sys.stderr.flush()

    print(f"Saving session to {session_filename}", file=sys.stderr)

    session_to_file(session, session_filename)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
