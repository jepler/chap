import sys
import os
import datetime

import platformdirs
import click

import traceback

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, MarkdownViewer, Input

from . import ask, User, Assistant
from .session import Session

def last_session():
    result = max(platformdirs.user_cache_path().glob("*.json"), key=lambda p:p.stat().st_mtime)
    print(result)
    return result
    
def markdown_for_step(step):
    return MarkdownViewer(format(step.content), classes='role_' + step.role)

class Tui(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        Binding('ctrl+c,ctrl+q', "app.quit", "Quit", show=True)
    ]

    def __init__(self, session):
        super().__init__()
        self.session = session

    @property
    def scrollview(self):
        return self.query_one(ScrollView)

    @property   
    def input(self):   
        return self.query_one(Input)

    def compose(self):
        yield Footer()
        yield Input(placeholder="Prompt")

    async def on_mount(self) -> None:                                           
        try:
            self.mount_all([markdown_for_step(step) for step in self.session.session])
        except Exception as e:
            with open("/tmp/fnord", "wt") as f:
                print("oops", file=f)
                print(e, file=f)
                traceback.print_exception(type(e), e, e.__traceback__, file=f)
            raise
        #self.scrollview.scroll_y = self.scrollview.get_content_height()
        self.input.focus()                                            

    async def on_input_submitted(self, event) -> None:
        result = ask(self.session, event.value)
        if result is not None:
            self.input.value = ""
        doc = "\n\n".join(format(step) for step in self.session.session)
        self.input.value = ""
        self.mount_all([markdown_for_step(step) for step in self.session.session[-2:]])

@click.command
@click.option('--continue-session', '-s', type=click.Path(exists=True), default=None)
@click.option('--last', is_flag=True)
@click.option('--new-session', '-n', type=click.Path(exists=False), default=None)
@click.option('--system-message', '-S', type=str, default=None)
def main(continue_session, last, new_session, system_message):
    if bool(continue_session) + bool(last) + bool(new_session) > 1:
        raise SystemExit("--continue-session, --last and --new_session are mutually exclusive")

    if last:
        continue_session = last_session()
    if continue_session:
        session_filename = continue_session
        with open(session_filename, "r") as f:
            session = Session.from_json(f.read())
    else:
        session_filename = new_session or platformdirs.user_cache_path() / (datetime.datetime.now().isoformat().replace(':', '_') + ".json")
        print(f"note: Session is in {session_filename}")
        if system_message:
            session = Session.new_session(system_message)
        else: 
            session = Session.new_session()

    tui = Tui(session)
    tui.run()

    print('saving session')
    with open(session_filename, "w") as f:
        f.write(session.to_json())

if __name__ == '__main__':
    main()
