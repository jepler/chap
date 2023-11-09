# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT
# pylint: disable=import-outside-toplevel

import asyncio
import datetime
import importlib
import os
import pathlib
import pkgutil
import subprocess
from dataclasses import MISSING, dataclass, fields
from types import UnionType
from typing import Any, AsyncGenerator, Callable, cast

import click
import platformdirs
from simple_parsing.docstring import get_attribute_docstring
from typing_extensions import Protocol

from . import backends, commands  # pylint: disable=no-name-in-module
from .session import Message, Session, System, session_from_file

conversations_path = platformdirs.user_state_path("chap") / "conversations"
conversations_path.mkdir(parents=True, exist_ok=True)


class ABackend(Protocol):  # pylint: disable=too-few-public-methods
    def aask(self, session: Session, query: str) -> AsyncGenerator[str, None]:
        """Make a query, updating the session with the query and response, returning the query token by token"""


class Backend(ABackend, Protocol):
    parameters: Any
    system_message: str

    def ask(self, session: Session, query: str) -> str:
        """Make a query, updating the session with the query and response, returning the query"""


class AutoAskMixin:  # pylint: disable=too-few-public-methods
    """Mixin class for backends implementing aask"""

    def ask(self, session: Session, query: str) -> str:
        tokens: list[str] = []

        async def inner() -> None:
            # https://github.com/pylint-dev/pylint/issues/5761
            async for token in self.aask(session, query):  # type: ignore
                tokens.append(token)

        asyncio.run(inner())
        return "".join(tokens)


def last_session_path() -> pathlib.Path | None:
    result = max(
        conversations_path.glob("*.json"), key=lambda p: p.stat().st_mtime, default=None
    )
    return result


def new_session_path(opt_path: pathlib.Path | None = None) -> pathlib.Path:
    return opt_path or conversations_path / (
        datetime.datetime.now().isoformat().replace(":", "_") + ".json"
    )


def configure_api_from_environment(api_name: str, api: Backend) -> None:
    if not hasattr(api, "parameters"):
        return

    for field in fields(api.parameters):
        envvar = f"CHAP_{api_name.upper()}_{field.name.upper()}"
        value = os.environ.get(envvar)
        if value is None:
            continue
        try:
            tv = field.type(value)
        except ValueError as e:
            raise click.BadParameter(
                f"Invalid value for {field.name} with value {value}: {e}"
            ) from e
        setattr(api.parameters, field.name, tv)


def get_api(name: str = "openai_chatgpt") -> Backend:
    name = name.replace("-", "_")
    result = cast(
        Backend, importlib.import_module(f"{__package__}.backends.{name}").factory()
    )
    configure_api_from_environment(name, result)
    return result


def do_session_continue(
    ctx: click.Context, param: click.Parameter, value: pathlib.Path | None
) -> None:
    if value is None:
        return
    if ctx.obj.session is not None:
        raise click.BadParameter(
            "--continue-session, --last and --new-session are mutually exclusive",
            param=param,
        )
    ctx.obj.session = session_from_file(value)
    ctx.obj.session_filename = value


def do_session_last(
    ctx: click.Context, param: click.Parameter, value: bool
) -> None:  # pylint: disable=unused-argument
    if not value:
        return
    do_session_continue(ctx, param, last_session_path())


def do_session_new(
    ctx: click.Context, param: click.Parameter, value: pathlib.Path
) -> None:
    if ctx.obj.session is not None:
        if value is None:
            return
        raise click.BadParameter(
            "--continue-session, --last and --new-session are mutually exclusive",
            param=param,
        )
    session_filename = new_session_path(value)
    system_message = ctx.obj.system_message or ctx.obj.api.system_message
    ctx.obj.session = [System(system_message)]
    ctx.obj.session_filename = session_filename


def colonstr(arg: str) -> tuple[str, str]:
    if ":" not in arg:
        raise click.BadParameter("must be of the form 'name:value'")
    return cast(tuple[str, str], tuple(arg.split(":", 1)))


def set_system_message(  # pylint: disable=unused-argument
    ctx: click.Context, param: click.Parameter, value: str
) -> None:
    if value and value.startswith("@"):
        with open(value[1:], "r", encoding="utf-8") as f:
            value = f.read().rstrip()
    ctx.obj.system_message = value


def set_backend(  # pylint: disable=unused-argument
    ctx: click.Context, param: click.Parameter, value: str
) -> None:
    if value == "list":
        formatter = ctx.make_formatter()
        format_backend_list(formatter)
        click.utils.echo(formatter.getvalue().rstrip("\n"))
        ctx.exit()

    try:
        ctx.obj.api = get_api(value)
    except ModuleNotFoundError as e:
        raise click.BadParameter(str(e))


def format_backend_help(api: Backend, formatter: click.HelpFormatter) -> None:
    with formatter.section(f"Backend options for {api.__class__.__name__}"):
        rows = []
        for f in fields(api.parameters):
            name = f.name.replace("_", "-")
            default = f.default if f.default_factory is MISSING else f.default_factory()
            doc = get_attribute_docstring(type(api.parameters), f.name).docstring_below
            if doc:
                doc += " "
            doc += f"(Default: {default!r})"
            f_type = f.type
            if isinstance(f_type, UnionType):
                f_type = f_type.__args__[0]
            typename = f_type.__name__
            rows.append((f"-B {name}:{typename.upper()}", doc))
        formatter.write_dl(rows)


def set_backend_option(  # pylint: disable=unused-argument
    ctx: click.Context, param: click.Parameter, opts: list[tuple[str, str]]
) -> None:
    api = ctx.obj.api
    if not hasattr(api, "parameters"):
        raise click.BadParameter(
            f"{api.__class__.__name__} does not support parameters"
        )
    all_fields = dict((f.name.replace("_", "-"), f) for f in fields(api.parameters))

    def set_one_backend_option(kv: tuple[str, str]) -> None:
        name, value = kv
        field = all_fields.get(name)
        if field is None:
            raise click.BadParameter(f"Invalid parameter {name}")
        f_type = field.type
        if isinstance(f_type, UnionType):
            f_type = f_type.__args__[0]
        try:
            tv = f_type(value)
        except ValueError as e:
            raise click.BadParameter(
                f"Invalid value for {name} with value {value}: {e}"
            ) from e
        setattr(api.parameters, name, tv)

    for kv in opts:
        set_one_backend_option(kv)


def format_backend_list(formatter: click.HelpFormatter) -> None:
    all_backends = []
    for pi in pkgutil.walk_packages(backends.__path__):
        name = pi.name
        if not name.startswith("__"):
            all_backends.append(name)
    all_backends.sort()

    rows = []
    for name in all_backends:
        try:
            factory = importlib.import_module(f"{__package__}.backends.{name}").factory
        except ImportError as e:
            rows.append((name, str(e)))
        else:
            doc = getattr(factory, "__doc__", None)
            rows.append((name, doc or ""))

    with formatter.section("Available backends"):
        formatter.write_dl(rows)


def uses_session(f: click.decorators.FC) -> Callable[[], None]:
    f = click.option(
        "--continue-session",
        "-s",
        type=click.Path(exists=True),
        default=None,
        callback=do_session_continue,
        expose_value=False,
    )(f)
    f = click.option(
        "--last", is_flag=True, callback=do_session_last, expose_value=False
    )(f)
    return click.pass_obj(f)


def command_uses_existing_session(f: click.decorators.FC) -> click.Command:
    return click.command()(uses_session(f))


def command_uses_new_session(f_in: click.decorators.FC) -> click.Command:
    f = uses_session(f_in)
    f = click.option(
        "--new-session",
        "-n",
        type=click.Path(exists=False),
        default=None,
        callback=do_session_new,
        expose_value=False,
    )(f)
    return click.command()(f)


def version_callback(  # pylint: disable=unused-argument
    ctx: click.Context, param: click.Parameter, value: None
) -> None:
    if not value or ctx.resilient_parsing:
        return

    git_dir = pathlib.Path(__file__).parent.parent.parent / ".git"
    version: str
    if git_dir.exists():
        version = subprocess.check_output(
            ["git", f"--git-dir={git_dir}", "describe", "--tags", "--dirty"],
            encoding="utf-8",
        )
    else:
        try:
            # __version__ file is not generated yet during CI
            from .__version__ import __version__ as version  # type: ignore
        except ImportError:
            version = "unknown"
    prog_name = ctx.find_root().info_name
    click.utils.echo(
        f"{prog_name}, version {version}",
        color=ctx.color,
    )
    ctx.exit()


@dataclass
class Obj:
    api: Backend | None = None
    system_message: str | None = None
    session: list[Message] | None = None
    session_filename: pathlib.Path | None = None


class MyCLI(click.MultiCommand):
    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: click.Context | None = None,
        **extra: Any,
    ) -> click.Context:
        result = super().make_context(info_name, args, parent, obj=Obj(), **extra)
        return result

    def list_commands(self, ctx: click.Context) -> list[str]:
        rv = []
        for pi in pkgutil.walk_packages(commands.__path__):
            name = pi.name
            if not name.startswith("__"):
                rv.append(name)
        rv.sort()
        return rv

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command:
        try:
            return cast(
                click.Command,
                importlib.import_module("." + cmd_name, commands.__name__).main,
            )
        except ModuleNotFoundError as exc:
            raise click.UsageError(f"Invalid subcommand {cmd_name!r}", ctx) from exc

    def format_options(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        super().format_options(ctx, formatter)
        api = ctx.obj.api or get_api()
        if hasattr(api, "parameters"):
            format_backend_help(api, formatter)


main = MyCLI(
    help="Commandline interface to ChatGPT",
    params=[
        click.Option(
            ("--version",),
            is_flag=True,
            is_eager=True,
            help="Show the version and exit",
            callback=version_callback,
        ),
        click.Option(
            ("--system-message", "-S"),
            type=str,
            default=None,
            callback=set_system_message,
            expose_value=False,
        ),
        click.Option(
            ("--backend", "-b"),
            type=str,
            default="openai_chatgpt",
            callback=set_backend,
            expose_value=False,
            is_eager=True,
            envvar="CHAP_BACKEND",
            help="The back-end to use ('--backend list' for a list)",
        ),
        click.Option(
            ("--backend-option", "-B"),
            type=colonstr,
            callback=set_backend_option,
            expose_value=False,
            multiple=True,
        ),
    ],
)
