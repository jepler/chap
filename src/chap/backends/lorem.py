# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import random
from dataclasses import dataclass

from lorem_text import lorem

from ..session import Assistant, User


def ipartition(s, sep=" "):
    rest = s
    while rest:
        first, opt_sep, rest = rest.partition(sep)
        yield (first, opt_sep)


class Lorem:
    @dataclass
    class Parameters:
        delay_mu: float = 0.035
        """Average delay between tokens"""
        delay_sigma: float = 0.02
        """Standard deviation of token delay"""
        paragraph_lo: int = 1
        """Minimum response paragraph count"""
        paragraph_hi: int = 5
        """Maximum response paragraph count (inclusive)"""

    def __init__(self):
        self.parameters = self.Parameters()

    system_message = (
        "(It doesn't matter what you ask, this backend will respond with lorem)"
    )

    async def aask(self, session, query, *, max_query_size=5, timeout=60):
        data = self.ask(session, query, max_query_size=max_query_size, timeout=timeout)
        for word, opt_sep in ipartition(data):
            yield word + opt_sep
            await asyncio.sleep(
                random.gauss(self.parameters.delay_mu, self.parameters.delay_sigma)
            )

    def ask(
        self, session, query, *, max_query_size=5, timeout=60
    ):  # pylint: disable=unused-argument
        new_content = lorem.paragraphs(
            random.randint(self.parameters.paragraph_lo, self.parameters.paragraph_hi)
        ).replace("\n", "\n\n")
        session.session.extend([User(query), Assistant("".join(new_content))])
        return new_content


def factory():
    """That just prints 'lorem' text. Useful for testing."""
    return Lorem()
