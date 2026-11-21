"""SEO & Packaging: title, description, tags, hashtags, pinned-comment idea."""
import json
import re

from ..config import S
from ..llm import ask_json
from ..util import log

SYSTEM = """You are the SEO & Packaging specialist of a YouTube Shorts channel. Language: {lang}.
Create honest metadata that exactly matches the video (no misleading clickbait).
Return JSON: {{"title": str (max 65 chars, curiosity but truthful),
"summary": str (2 short sentences describing the video),
"tags": [str] (10-15 relevant search tags),
"hashtags": [str] (3-4 relevant hashtags),
"pinned_comment": str (a question that sparks discussion)}}"""

AI_NOTE = {
    "hi": "यह वीडियो AI की मदद से बनाया गया है (स्क्रिप्ट और आवाज़ AI-जनरेटेड हैं)।",
    "en": "This video was made with AI assistance (script and voice are AI-generated).",
}


def make(pick: dict, script: dict) -> dict:
    user = json.dumps({"topic": pick, "script": script["full_text"]}, ensure_ascii=False)
    m = ask_json(SYSTEM.format(lang=S.lang_label), user, max_tokens=1500)

    title = re.sub(r"[<>]", "", m.get("title", pick.get("topic", "Explained"))).strip()[:95]

    tags, total = [], 0
    for t in m.get("tags", []):
        t = re.sub(r"[<>#]", "", str(t)).strip()
        if t and total + len(t) + 1 <= 450:
            tags.append(t)
            total += len(t) + 1

    hashtags = ["#Shorts"]
    for h in m.get("hashtags", [])[:4]:
        h = "#" + re.sub(r"[^\w]", "", str(h))
        if len(h) > 1 and h.lower() not in [x.lower() for x in hashtags]:
            hashtags.append(h)

    body = re.sub(r"[<>]", "", m.get("summary", "")).strip()
    meta = {
        "title": title,
        "body": body,
        "tags": tags,
        "hashtags": hashtags,
        "pinned_comment": m.get("pinned_comment", ""),
    }
    meta["description"] = build_description(meta, [])
    log("SEO", f"Title: {title}")
    return meta


def build_description(meta: dict, assets: list[dict]) -> str:
    parts = [meta["body"]]
    if S.disclose_ai:
        parts.append(AI_NOTE.get(S.language, AI_NOTE["en"]))
    srcs = sorted({a["source"].capitalize() for a in assets if a.get("source") in ("pexels", "pixabay", "wikimedia")})
    if srcs:
        parts.append("Stock footage: " + ", ".join(srcs) + ".")
    parts.append(" ".join(meta["hashtags"]))
    return "\n\n".join(p for p in parts if p)


def add_credits(meta: dict, assets: list[dict]) -> dict:
    meta["description"] = build_description(meta, assets)
    return meta
