# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import random
from dataclasses import dataclass
from typing import AsyncGenerator, Iterable, cast

# lorem is not type annotated
from lorem_text import lorem  # type: ignore

from ..core import Backend
from ..session import Assistant, Session, User


def ipartition(s: str, sep: str = " ") -> Iterable[tuple[str, str]]:
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

    def __init__(self) -> None:
        self.parameters = self.Parameters()

    system_message = (
        "(It doesn't matter what you ask, this backend will respond with lorem)"
    )

    async def aask(
        self,
        session: Session,
        query: str,
    ) -> AsyncGenerator[str, None]:
        data = self.ask(session, query)[-1]
        for word, opt_sep in ipartition(data):
            yield word + opt_sep
            await asyncio.sleep(
                random.gauss(self.parameters.delay_mu, self.parameters.delay_sigma)
            )

    def ask(
        self,
        session: Session,
        query: str,
    ) -> str:  # pylint: disable=unused-argument
        new_content = cast(
            str,
            lorem.paragraphs(
                random.randint(
                    self.parameters.paragraph_lo, self.parameters.paragraph_hi
                )
            ),
        ).replace("\n", "\n\n")
        session.extend([User(query), Assistant("".join(new_content))])
        return session[-1].content


def factory() -> Backend:
    """That just prints 'lorem' text. Useful for testing."""
    return Lorem()
