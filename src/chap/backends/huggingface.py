# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator

import httpx

from ..core import AutoAskMixin, Backend
from ..key import get_key
from ..session import Assistant, Role, Session, User


class HuggingFace(AutoAskMixin):
    @dataclass
    class Parameters:
        url: str = "https://api-inference.huggingface.co"
        model: str = "mistralai/Mistral-7B-Instruct-v0.1"
        max_new_tokens: int = 250
        start_prompt: str = """<s>[INST] <<SYS>>\n"""
        after_system: str = "\n<</SYS>>\n\n"
        after_user: str = """ [/INST] """
        after_assistant: str = """ </s><s>[INST] """
        stop_token_id = 2

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

    async def chained_query(
        self, inputs: Any, timeout: float
    ) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            while inputs:
                params = {
                    "inputs": inputs,
                    "stream": True,
                }
                inputs = None
                async with client.stream(
                    "POST",
                    f"{self.parameters.url}/models/{self.parameters.model}",
                    json=params,
                    headers={
                        "Authorization": f"Bearer {self.get_key()}",
                    },
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data:"):
                                data = line.removeprefix("data:").strip()
                                j = json.loads(data)
                                token = j.get("token", {})
                                inputs = j.get("generated_text", inputs)
                                if token.get("id") == self.parameters.stop_token_id:
                                    return
                                yield token.get("text", "")
                    else:
                        yield f"\nFailed with {response=!r}"
                        return

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
        new_content: list[str] = []
        inputs = self.make_full_query(session + [User(query)], max_query_size)
        try:
            async for content in self.chained_query(inputs, timeout=timeout):
                if not new_content:
                    content = content.lstrip()
                if content:
                    if not new_content:
                        content = content.lstrip()
                    if content:
                        new_content.append(content)
                        yield content

        except httpx.HTTPError as e:
            content = f"\nException: {e!r}"
            new_content.append(content)
            yield content

        session.extend([User(query), Assistant("".join(new_content))])

    @classmethod
    def get_key(cls) -> str:
        return get_key("huggingface_api_token")


def factory() -> Backend:
    """Uses the huggingface text-generation-interface web API"""
    return HuggingFace()
