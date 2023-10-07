#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import pathlib
import sys

sys.path[0] = str(pathlib.Path(__file__).parent / "src")

if __name__ == "__main__":
    # pylint: disable=import-error,no-name-in-module
    from chap.core import main

    main()
else:
    raise ImportError(
        "this script exists to facilitate running 'python -mchap' in the top directory; it should not be imported"
    )
