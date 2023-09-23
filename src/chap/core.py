# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT
# pylint: disable=import-outside-toplevel

import datetime
import importlib
import pathlib
import pkgutil
import subprocess
from dataclasses import dataclass, fields

import click
import platformdirs

from . import commands  # pylint: disable=no-name-in-module
from .session import Session

conversations_path = platformdirs.user_state_path("chap") / "conversations"
conversations_path.mkdir(parents=True, exist_ok=True)


def last_session_path():
    result = max(
        conversations_path.glob("*.json"), key=lambda p: p.stat().st_mtime, default=None
    )
    print(result)
    return result


def new_session_path(opt_path=None):
    return opt_path or conversations_path / (
        datetime.datetime.now().isoformat().replace(":", "_") + ".json"
    )


def get_api(name="openai_chatgpt"):
    return importlib.import_module(f"{__package__}.backends.{name}").factory()


def ask(*args, **kw):
    return get_api().ask(*args, **kw)


def aask(*args, **kw):
    return get_api().aask(*args, **kw)


def do_session_continue(ctx, param, value):
    if value is None:
        return
    if ctx.obj.session is not None:
        raise click.BadParameter(
            param, "--continue-session, --last and --new-session are mutually exclusive"
        )
    with open(value, "r", encoding="utf-8") as f:
        ctx.obj.session = Session.from_json(f.read())  # pylint: disable=no-member
    ctx.obj.session_filename = value


def do_session_last(ctx, param, value):  # pylint: disable=unused-argument
    if not value:
        return
    do_session_continue(ctx, param, last_session_path())


def do_session_new(ctx, param, value):
    if ctx.obj.session is not None:
        if value is None:
            return
        raise click.BadOptionUsage(
            param, "--continue-session, --last and --new-session are mutually exclusive"
        )
    session_filename = new_session_path(value)
    system_message = ctx.obj.system_message or ctx.obj.api.system_message
    ctx.obj.session = Session.new_session(system_message)
    ctx.obj.session_filename = session_filename


def colonstr(arg):
    if ":" not in arg:
        raise click.BadParameter("must be of the form 'name:value'")
    return arg.split(":", 1)


def set_system_message(ctx, param, value):  # pylint: disable=unused-argument
    ctx.obj.system_message = value


def set_backend(ctx, param, value):  # pylint: disable=unused-argument
    ctx.obj.api = get_api(value)


def set_backend_option(ctx, param, opts):  # pylint: disable=unused-argument
    api = ctx.obj.api
    if not hasattr(api, "parameters"):
        raise click.BadParameter(
            f"{api.__class__.__name__} does not support parameters"
        )
    all_fields = dict((f.name, f) for f in fields(api.parameters))

    def set_one_backend_option(kv):
        name, value = kv
        field = all_fields.get(name)
        if field is None:
            raise click.BadParameter(f"Invalid parameter {name}")
        try:
            tv = field.type(value)
        except ValueError as e:
            raise click.BadParameter(
                f"Invalid value for {name} with value {value}: {e}"
            ) from e
        setattr(api.parameters, name, tv)

    for kv in opts:
        set_one_backend_option(kv)


def uses_session(f):
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
    f = click.pass_obj(f)
    return f


def uses_existing_session(f):
    f = uses_session(f)
    return f


def uses_new_session(f):
    f = click.option(
        "--system-message",
        "-S",
        type=str,
        default=None,
        callback=set_system_message,
        expose_value=False,
    )(f)
    f = click.option(
        "--backend",
        "-b",
        type=str,
        default="openai_chatgpt",
        callback=set_backend,
        expose_value=False,
        is_eager=True,
    )(f)
    f = click.option(
        "--backend-option",
        "-B",
        type=colonstr,
        callback=set_backend_option,
        expose_value=False,
        multiple=True,
    )(f)
    f = uses_existing_session(f)
    f = click.option(
        "--new-session",
        "-n",
        type=click.Path(exists=False),
        default=None,
        callback=do_session_new,
        expose_value=False,
    )(f)
    return f


def version_callback(ctx, param, value) -> None:  # pylint: disable=unused-argument
    if not value or ctx.resilient_parsing:
        return

    git_dir = pathlib.Path(__file__).parent.parent.parent / ".git"
    if git_dir.exists():
        version = subprocess.check_output(
            ["git", f"--git-dir={git_dir}", "describe", "--tags", "--dirty"],
            encoding="utf-8",
        )
    else:
        try:
            from .__version__ import __version__ as version
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
    api: object = None
    system_message: object = None
    session: Session | None = None


class MyCLI(click.MultiCommand):
    def make_context(self, info_name, args, parent=None, **extra):
        result = super().make_context(info_name, args, parent, **extra)
        result.obj = Obj()
        return result

    def list_commands(self, ctx):
        rv = []
        for pi in pkgutil.walk_packages(commands.__path__):
            name = pi.name
            if not name.startswith("__"):
                rv.append(name)
        rv.sort()
        return rv

    def get_command(self, ctx, cmd_name):
        try:
            return importlib.import_module("." + cmd_name, commands.__name__).main
        except ModuleNotFoundError as exc:
            raise click.UsageError(f"Invalid subcommand {cmd_name!r}", ctx) from exc


main = MyCLI(
    help="Commandline interface to ChatGPT",
    params=[
        click.Option(
            ("--version",),
            is_flag=True,
            is_eager=True,
            help="Show the version and exit",
            callback=version_callback,
        )
    ],
)
