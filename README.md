<!--
SPDX-FileCopyrightText: 2021 Jeff Epler

SPDX-License-Identifier: MIT
-->
[![Test](https://github.com/jepler/chap/actions/workflows/test.yml/badge.svg)](https://github.com/jepler/chap/actions/workflows/test.yml)
[![Release chap](https://github.com/jepler/chap/actions/workflows/release.yml/badge.svg?event=release)](https://github.com/jepler/chap/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/chap)](https://pypi.org/project/chap/)

# chap - A Python interface to chatgpt, including a terminal user interface (tui)

![Chap screencast](https://github.com/jepler/chap/blob/main/chap.gif)

## System requirements

Chap is developed on Linux with Python 3.9. Due to use of the `list[int]` style of type hints, it is known not to work on 3.8 and newer; it is hoped that it works on newer versions but is untested.

## installation

Install with e.g., `pipx install chap`

## configuration

Put your OpenAI API key in the platform configuration directory for chap, e.g., on linux/unix systems at `~/.config/chap/openai_api_key`

## commandline usage

 * chap ask "What advice would you give a 20th century human visiting the 21st century for the first time?"

 * chap render --last

 * chap import chatgpt-style-chatlog.json

## interactive terminal usage
 * chap tui

## Sessions & Commandline Parameters

Details of session handling & commandline arguments are in flux.

By default, a new session is created. It is saved to the user's state directory
(e.g., `~/.local/state/chap` on linux/unix systems).

You can specify the session filename for a new session with `-n` or to re-open
an existing session with `-s`. Or, you can continue the last session with
`--last`.

You can set the "system message" with the `-S` flag.

You can select the text generating backend with the `-b` flag:
 * openai\_chatgpt: the default, paid API, best quality results
 * textgen: Works with https://github.com/oobabooga/text-generation-webui and can run locally with various models, basic and low quality. Needs the server URL in *$configuration_directory/textgen\_url*.
 * lorem: local non-AI lorem generator for testing

## Importing from ChatGPT

The userscript https://github.com/pionxzh/chatgpt-exporter can export chat logs from chat.openai.com in a json format.
This format is different than chap's, especially since chap currently only represents a single branch of conversation in one log.
You can use the `chap import` command to import all the branches of a chatgpt-style chatlog in json format into a series of chap-style chat logs.
