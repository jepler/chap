import sys
import requests
from .session import Assistant, User, Message, Session
from .key import get_key

def ask(session, query, *, max_query_size=5, timeout=60):
    full_prompt = Session(session.session + [User(query)])
    del full_prompt.session[1:-max_query_size]

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        json={"model": "gpt-3.5-turbo", "messages": full_prompt.to_dict()['session']},
        headers={
            "Authorization": f"Bearer {get_key()}",
        },
        timeout=timeout,
    )

    if response.status_code != 200:
        print("Failure", response.status_code, r.text)
        return None

    try:
        j = response.json()
        result = j["choices"][0]["message"]["content"]
    except (KeyError, IndexError, requests.exceptions.JSONDecodeError):
        print("Failure", response.status_code, r.text)
        return None

    session.session.extend([User(query), Assistant(result)])
    return result

if sys.stdout.isatty():
    bold='\033[1m'
    nobold='\033[m'
else:
    bold = nobold = ''

def verbose_ask(session, q, **kw):
    print(f"{bold}{q}{nobold}")
    print()
    print(result := ask(session, q, **kw))
    print()
    return result
