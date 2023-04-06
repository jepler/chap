# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT
# pylint: disable=import-outside-toplevel

import importlib
import pathlib
import pkgutil
import subprocess

import click

from . import commands  # pylint: disable=no-name-in-module


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


class MyCLI(click.MultiCommand):
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

if __name__ == "__main__":
    main()
