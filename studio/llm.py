import json
import re
import time

from anthropic import Anthropic, AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError

from .config import S

_client = None


def _c() -> Anthropic:
    global _client
    if _client is None:
        if not S.anthropic_key:
            raise RuntimeError("ANTHROPIC_API_KEY is missing. Add it to your .env file.")
        _client = Anthropic(api_key=S.anthropic_key, max_retries=5)
    return _client


def ask(system: str, user: str, max_tokens: int = 4000) -> str:
    last = None
    for attempt in range(3):
        try:
            r = _c().messages.create(
                model=S.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        except (AuthenticationError, PermissionDeniedError, BadRequestError, NotFoundError) as e:
            raise RuntimeError(
                f"Claude API rejected the request ({type(e).__name__}). Check ANTHROPIC_API_KEY in .env "
                f"(new key, no spaces/quotes), credits in the Anthropic console, and CLAUDE_MODEL. Details: {e}"
            ) from e
        except Exception as e:  # network / rate limit
            last = e
            wait = 20 * (attempt + 1)
            print(f"[Claude API] {type(e).__name__}: {e} -> waiting {wait}s then retrying", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"Claude API failed: {last}")


def _extract_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    start, end = t.find("{"), t.rfind("}")
    return json.loads(t[start : end + 1])


def ask_json(system: str, user: str, max_tokens: int = 4000) -> dict:
    sys2 = system + "\n\nReply with ONE valid JSON object only. No markdown fences, no commentary."
    last = None
    for _ in range(3):
        txt = ask(sys2, user, max_tokens)
        try:
            return _extract_json(txt)
        except Exception as e:
            last = e
            user += "\n\n(Your previous reply was not valid JSON. Return only the JSON object.)"
    raise RuntimeError(f"Claude did not return valid JSON: {last}")
