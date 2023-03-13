# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import importlib
import pkgutil

import click

from . import commands  # pylint: disable=no-name-in-module


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
        return importlib.import_module("." + cmd_name, commands.__name__).main


main = MyCLI(help="Commandline interface to ChatGPT")

if __name__ == "__main__":
    main()
