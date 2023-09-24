# SPDX-FileCopyrightText: 2023 Jeff Epler <jepler@gmail.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import json
import uuid

import websockets

from ..key import get_key
from ..session import Assistant, Session, User


class Textgen:
    def __init__(self):
        self.server = get_key("textgen_url", "textgen server URL")

    system_message = """\
A dialog, where USER interacts with AI. AI is helpful, kind, obedient, honest, and knows its own limits.

USER: Hello, AI.

AI: Hello! How can I assist you today?"""

    async def aask(
        self, session, query, *, max_query_size=5, timeout=60
    ):  # pylint: disable=unused-argument,too-many-locals,too-many-branches
        params = {
            "max_new_tokens": 200,
            "do_sample": True,
            "temperature": 0.5,
            "top_p": 0.9,
            "typical_p": 1,
            "repetition_penalty": 1.05,
            "top_k": 0,
            "min_length": 0,
            "no_repeat_ngram_size": 0,
            "num_beams": 1,
            "penalty_alpha": 0,
            "length_penalty": 1,
            "early_stopping": False,
        }
        session_hash = str(uuid.uuid4())

        role_map = {
            "user": "USER: ",
            "assistant": "AI: ",
        }
        full_prompt = Session(session.session + [User(query)])
        del full_prompt.session[1:-max_query_size]
        new_data = old_data = full_query = (
            "\n".join(
                f"{role_map.get(q.role,'')}{q.content}\n" for q in full_prompt.session
            )
            + f"\n{role_map.get('assistant')}"
        )
        try:
            async with websockets.connect(  # pylint: disable=no-member
                f"ws://{self.server}:7860/queue/join"
            ) as websocket:
                while content := json.loads(await websocket.recv()):
                    if content["msg"] == "send_hash":
                        await websocket.send(
                            json.dumps({"session_hash": session_hash, "fn_index": 7})
                        )
                    if content["msg"] == "estimation":
                        pass
                    if content["msg"] == "send_data":
                        await websocket.send(
                            json.dumps(
                                {
                                    "session_hash": session_hash,
                                    "fn_index": 7,
                                    "data": [
                                        full_query,
                                        params["max_new_tokens"],
                                        params["do_sample"],
                                        params["temperature"],
                                        params["top_p"],
                                        params["typical_p"],
                                        params["repetition_penalty"],
                                        params["top_k"],
                                        params["min_length"],
                                        params["no_repeat_ngram_size"],
                                        params["num_beams"],
                                        params["penalty_alpha"],
                                        params["length_penalty"],
                                        params["early_stopping"],
                                    ],
                                }
                            )
                        )
                    if content["msg"] == "process_starts":
                        pass
                    if content["msg"] in ("process_generating", "process_completed"):
                        new_data = content["output"]["data"][0]
                        all_response = new_data[len(full_query) :]
                        if "USER:" in all_response:
                            new_data = new_data[
                                : len(full_query) + all_response.find("USER:")
                            ]
                            content["msg"] = "process_completed"
                        elif new_data.endswith("USER"):
                            new_data = new_data.removesuffix("USER")
                        elif new_data.endswith("USE"):
                            new_data = new_data.removesuffix("USE")
                        elif new_data.endswith("US"):
                            new_data = new_data.removesuffix("US")
                        elif new_data.endswith("U"):
                            new_data = new_data.removesuffix("U")

                        delta = new_data[len(old_data) :]
                        if delta:
                            yield delta
                            old_data = new_data
                        # You can search for your desired end indicator and
                        #  stop generation by closing the websocket here
                        if content["msg"] == "process_completed":
                            break
        except Exception as e:  # pylint: disable=broad-exception-caught
            content = f"\nException: {e!r}"
            new_data += content
            yield content

        all_response = new_data[len(full_query) :]
        session.session.extend([User(query), Assistant(all_response)])

    def ask(self, session, query, *, max_query_size=5, timeout=60):
        asyncio.run(
            self.aask(session, query, max_query_size=max_query_size, timeout=timeout)
        )
        return session.session[-1].message


def factory():
    """Uses the textgen completion API"""
    return Textgen()
