# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

.PHONY: mypy
mypy: venv/bin/mypy
	venv/bin/mypy

# Update CONTRIBUTING.md if these commands change
venv/bin/mypy:
	python -mvenv venv
	venv/bin/pip install -r requirements.txt 'mypy!=1.7.0'

.PHONY: clean
clean:
	rm -rf venv
