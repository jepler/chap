# SPDX-FileCopyrightText: 2024 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import json
from dataclasses import dataclass
from typing import AsyncGenerator, Any

import httpx

from ..core import AutoAskMixin
from ..key import get_key
from ..session import Assistant, Session, User


class Mistral(AutoAskMixin):
    @dataclass
    class Parameters:
        url: str = "https://api.mistral.ai"
        model: str = "open-mistral-7b"
        max_new_tokens: int = 1000

    def __init__(self) -> None:
        super().__init__()
        self.parameters = self.Parameters()

    system_message = """\
Answer each question accurately and thoroughly.
"""

    def make_full_query(self, messages: Session, max_query_size: int) -> dict[str, Any]:
        messages = [m for m in messages if m.content]
        del messages[1:-max_query_size]
        result = dict(
            model=self.parameters.model,
            max_tokens=self.parameters.max_new_tokens,
            messages=[dict(role=str(m.role), content=m.content) for m in messages],
            stream=True,
        )
        return result

    async def aask(
        self,
        session: Session,
        query: str,
        *,
        max_query_size: int = 5,
        timeout: float = 180,
    ) -> AsyncGenerator[str, None]:
        new_content: list[str] = []
        params = self.make_full_query(session + [User(query)], max_query_size)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.parameters.url}/v1/chat/completions",
                    json=params,
                    headers={
                        "Authorization": f"Bearer {self.get_key()}",
                        "content-type": "application/json",
                        "accept": "application/json",
                        "model": "application/json",
                    },
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data:"):
                                data = line.removeprefix("data:").strip()
                                if data == "[DONE]":
                                    break
                                j = json.loads(data)
                                content = (
                                    j.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content", "")
                                )
                                if content:
                                    new_content.append(content)
                                    yield content
                    else:
                        content = f"\nFailed with {response=!r}"
                        new_content.append(content)
                        yield content
                        async for line in response.aiter_lines():
                            new_content.append(line)
                            yield line
        except httpx.HTTPError as e:
            content = f"\nException: {e!r}"
            new_content.append(content)
            yield content

        session.extend([User(query), Assistant("".join(new_content))])

    @classmethod
    def get_key(cls) -> str:
        return get_key("mistral_api_key")


factory = Mistral
