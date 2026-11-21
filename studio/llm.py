import json
import re
import time

import requests
from anthropic import Anthropic, AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError

from .config import S

_client = None
_last_gemini = 0.0


def _c() -> Anthropic:
    global _client
    if _client is None:
        if not S.anthropic_key:
            raise RuntimeError("ANTHROPIC_API_KEY is missing. Add it to your .env file (or use GEMINI_API_KEY).")
        _client = Anthropic(api_key=S.anthropic_key, max_retries=5)
    return _client


def _ask_anthropic(system: str, user: str, max_tokens: int) -> str:
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


def _ask_gemini(system: str, user: str, max_tokens: int, json_mode: bool) -> str:
    """Google Gemini via REST (free tier works with a Google AI Studio key)."""
    global _last_gemini
    if not S.gemini_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Get a free key at https://aistudio.google.com/apikey")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{S.gemini_model}:generateContent"
    gen = {"maxOutputTokens": max_tokens * 2}  # headroom: some models spend tokens on thinking
    if json_mode:
        gen["responseMimeType"] = "application/json"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": gen,
    }
    last = None
    for attempt in range(5):
        gap = 4.5 - (time.time() - _last_gemini)  # stay under free-tier 15 requests/minute
        if gap > 0:
            time.sleep(gap)
        try:
            r = requests.post(url, headers={"x-goog-api-key": S.gemini_key}, json=body, timeout=120)
        except requests.RequestException as e:
            last = e
            time.sleep(10)
            continue
        _last_gemini = time.time()
        if r.status_code in (400, 401, 403, 404):
            raise RuntimeError(
                f"Gemini rejected the request (HTTP {r.status_code}). Check GEMINI_API_KEY and GEMINI_MODEL "
                f"({S.gemini_model}) in .env. Details: {r.text[:400]}"
            )
        if r.status_code == 429 or r.status_code >= 500:
            wait = 20 * (attempt + 1)
            print(f"[Gemini API] HTTP {r.status_code} (rate limit / busy) -> waiting {wait}s then retrying", flush=True)
            last = r.text[:300]
            time.sleep(wait)
            continue
        data = r.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts if not p.get("thought"))
        except (KeyError, IndexError):
            last = f"Empty/blocked response: {str(data)[:300]}"
            time.sleep(5)
    raise RuntimeError(f"Gemini API failed: {last}")


def ask(system: str, user: str, max_tokens: int = 4000, json_mode: bool = False) -> str:
    if S.llm_provider == "gemini":
        return _ask_gemini(system, user, max_tokens, json_mode)
    return _ask_anthropic(system, user, max_tokens)


def _extract_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    start, end = t.find("{"), t.rfind("}")
    return json.loads(t[start : end + 1])


def ask_json(system: str, user: str, max_tokens: int = 4000) -> dict:
    sys2 = system + "\n\nReply with ONE valid JSON object only. No markdown fences, no commentary."
    last = None
    for _ in range(3):
        txt = ask(sys2, user, max_tokens, json_mode=True)
        try:
            return _extract_json(txt)
        except Exception as e:
            last = e
            user += "\n\n(Your previous reply was not valid JSON. Return only the JSON object.)"
    raise RuntimeError(f"The AI did not return valid JSON: {last}")
