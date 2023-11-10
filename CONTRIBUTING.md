<!--
SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>

SPDX-License-Identifier: MIT
-->

# Contributing

Please feel free to submit pull requests or open issues to improve this project.

There's no particular roadmap for chap, it was created to scratch the original developer's itch but has been useful to others as well.
If you're looking for a way to contribute, check out the open issues.
If you want to discuss a possible enhancement before beginning work, opening a fresh issue is a good way to start a dialog about your idea.

## Code style & linting with pre-commit

This project uses [pre-commit](https://pre-commit.com/) to maintain the code's style and perform some quality checks.
First, install pre-commit: `pip install pre-commit`.
Then, enable pre-commit via git "hooks" so that (most of the time) pre-commit checks are performed at the time a git commit is made: `pre-commit install`.
If necessary, you can run pre-commit checks manually for one or more files: `pre-commit run --all` or `pre-commit run --files src/chap/main.py`.

Some tools (e.g., black) will automatically update the working files with whatever changes they recommend.
Other tools (e.g., pylint) will just tell you what is wrong and require your intervention to fix it.
It is acceptable to use hints like `#  pylint: ignore=diagnostic-kind` when it's preferable to actually resolving the reported problem
(e.g., if the report is spurious or a non-standard construct is used for well-considered reasons)

When you create a pull request, `pre-commit run --all` is run in a standardized environment, which occasionally catches things that were not seen locally.
That green checkmark in github actions is the final arbiter of whether the code is pre-commit clean.

## Type checking with mypy

This project uses [mypy](https://www.mypy-lang.org/) for type-checking.
If your system has `make`, you can type-check the project with: `make`.
Otherwise, you need to perform several setup steps:
 * create a virtual environment at "venv": `python -mvenv venv`
 * install dependencies in the virtual environment: `venv/bin/pip install -r requirements.txt 'mypy!=1.7.0'`

Then, type check with: `venv/bin/mypy`

When you create a pull request, mypy is run in a standardized environment, which occasionally catches things that were not seen locally.
That green checkmark in github actions is the final arbiter of whether the code is mypy clean.
