"""Trend Scout: finds what is trending and picks ONE safe, explainable topic."""
import json
import xml.etree.ElementTree as ET

import requests

from ..config import DATA, S
from ..llm import ask_json
from ..util import load_json, log

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

SYSTEM = """You are the Trend Scout of a YouTube Shorts explainer studio.
From the trending items given, pick the ONE topic best suited to a ~45-second, fact-based explainer Short.
PREFER: science, technology, space, nature, business/economy basics, sports events, entertainment releases,
culture, festivals, and 'why/how is X happening' explainers.
REJECT: deaths, accidents, crimes or tragedies, wars/conflicts, elections or party politics, private individuals,
medical or health claims, investing/gambling/betting tips, adult content, rumours, anything you cannot explain with solid facts.
Do NOT pick topics already covered (list provided).
If nothing is suitable, set "evergreen": true and propose a fascinating evergreen explainer topic instead (fact-based, safe).
Return JSON: {"topic": str, "angle": str (the specific why/how question the video answers),
"why_now": str, "news_context": [str], "evergreen": bool}"""


def fetch_trends(geo: str | None = None, limit: int = 25) -> list[dict]:
    geo = geo or S.geo
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        r = requests.get(url, headers=UA, timeout=25)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        log("Trend Scout", f"Google Trends feed unavailable ({e}). Falling back to evergreen topics.")
        return []
    out = []
    for item in root.iter("item"):
        d = {"title": "", "traffic": "", "news": []}
        for ch in item:
            tag = ch.tag.split("}")[-1]
            if tag == "title":
                d["title"] = (ch.text or "").strip()
            elif tag == "approx_traffic":
                d["traffic"] = (ch.text or "").strip()
            elif tag == "news_item":
                n = {x.tag.split("}")[-1]: (x.text or "").strip() for x in ch}
                d["news"].append(
                    {
                        "title": n.get("news_item_title", ""),
                        "snippet": n.get("news_item_snippet", ""),
                        "source": n.get("news_item_source", ""),
                    }
                )
        if d["title"]:
            out.append(d)
        if len(out) >= limit:
            break
    return out


def pick_topic(override: str | None = None) -> dict:
    history = load_json(DATA / "history.json", []) or []
    used = [h.get("topic", "") for h in history[-60:]]
    niche = f"Channel niche preference: {S.niche}\n" if S.niche else ""

    if override:
        log("Trend Scout", f"Using your topic: {override}")
        user = f"{niche}The creator chose this topic: {override}\nBuild the angle for it. Set evergreen=false."
    else:
        trends = fetch_trends()
        log("Trend Scout", f"Fetched {len(trends)} trending items for {S.geo}")
        user = (
            f"{niche}Today's trending items ({S.geo}):\n{json.dumps(trends, ensure_ascii=False)}\n\n"
            f"Already covered (skip): {json.dumps(used, ensure_ascii=False)}"
        )
    pick = ask_json(SYSTEM, user, max_tokens=1500)
    log("Trend Scout", f"Topic: {pick.get('topic')}  |  Angle: {pick.get('angle')}")
    return pick
