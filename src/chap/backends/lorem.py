# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import random

from lorem_text import lorem

from ..session import Assistant, User


def ipartition(s, sep=" "):
    rest = s
    while rest:
        first, opt_sep, rest = rest.partition(sep)
        yield (first, opt_sep)


class Lorem:
    system_message = (
        "(It doesn't matter what you ask, this backend will respond with lorem)"
    )

    async def aask(self, session, query, *, max_query_size=5, timeout=60):
        data = self.ask(session, query, max_query_size=max_query_size, timeout=timeout)
        for word, opt_sep in ipartition(data):
            yield word + opt_sep
            await asyncio.sleep(random.uniform(0.02, 0.05))

    def ask(
        self, session, query, *, max_query_size=5, timeout=60
    ):  # pylint: disable=unused-argument
        new_content = lorem.paragraphs(3).replace("\n", "\n\n")
        session.session.extend([User(query), Assistant("".join(new_content))])
        return new_content


def factory():
    return Lorem()
