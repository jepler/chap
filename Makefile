# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

.PHONY: mypy
mypy: venv/bin/mypy
	venv/bin/mypy --strict --no-warn-unused-ignores -p chap

venv/bin/mypy:
	python -mvenv venv
	venv/bin/pip install -r requirements.txt mypy

.PHONY: clean
clean:
	rm -rf venv
