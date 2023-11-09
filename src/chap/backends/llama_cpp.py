# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import json
from dataclasses import dataclass
from typing import AsyncGenerator

import httpx

from ..core import AutoAskMixin, Backend
from ..session import Assistant, Role, Session, User


class LlamaCpp(AutoAskMixin):
    @dataclass
    class Parameters:
        url: str = "http://localhost:8080/completion"
        """The URL of a llama.cpp server's completion endpoint."""

        start_prompt: str = """<s>[INST] <<SYS>>\n"""
        after_system: str = "\n<</SYS>>\n\n"
        after_user: str = """ [/INST] """
        after_assistant: str = """ </s><s>[INST] """

    def __init__(self) -> None:
        super().__init__()
        self.parameters = self.Parameters()

    system_message = """\
A dialog, where USER interacts with AI. AI is helpful, kind, obedient, honest, and knows its own limits.
"""

    def make_full_query(self, messages: Session, max_query_size: int) -> str:
        del messages[1:-max_query_size]
        result = [self.parameters.start_prompt]
        for m in messages:
            content = (m.content or "").strip()
            if not content:
                continue
            result.append(content)
            if m.role == Role.SYSTEM:
                result.append(self.parameters.after_system)
            elif m.role == Role.ASSISTANT:
                result.append(self.parameters.after_assistant)
            elif m.role == Role.USER:
                result.append(self.parameters.after_user)
        full_query = "".join(result)
        return full_query

    async def aask(
        self,
        session: Session,
        query: str,
        *,
        max_query_size: int = 5,
        timeout: float = 180,
    ) -> AsyncGenerator[
        str, None
    ]:  # pylint: disable=unused-argument,too-many-locals,too-many-branches
        params = {
            "prompt": self.make_full_query(session + [User(query)], max_query_size),
            "stream": True,
            "stop": ["</s>", "<s>", "[INST]"],
        }
        new_content: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    self.parameters.url,
                    json=params,
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data:"):
                                data = line.removeprefix("data:").strip()
                                j = json.loads(data)
                                content = j.get("content")
                                if not new_content:
                                    content = content.lstrip()
                                if content:
                                    new_content.append(content)
                                    yield content
                                if j.get("stop"):
                                    break
                    else:
                        content = f"\nFailed with {response=!r}"
                        new_content.append(content)
                        yield content

        except httpx.HTTPError as e:
            content = f"\nException: {e!r}"
            new_content.append(content)
            yield content

        session.extend([User(query), Assistant("".join(new_content))])


def factory() -> Backend:
    """Uses the llama.cpp completion web API"""
    return LlamaCpp()
