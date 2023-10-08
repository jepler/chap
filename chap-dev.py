#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

# chap-dev.py - Simple shim script to demonstrate how to use the chap library.

import pathlib
import sys

# Ensure the 'src' directory is on the system path so we can import 'chap'
project_root = pathlib.Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    # pylint: disable=import-error,no-name-in-module
    from chap.core import main

    main()
else:
    raise ImportError("'chap-dev.py' is meant for direct execution, not for import.")
