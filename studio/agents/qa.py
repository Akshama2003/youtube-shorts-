"""QA & Compliance: technical checks + copyright / YouTube-policy / fact review. Nothing is published unless this passes."""
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from ..config import DATA, S
from ..llm import ask_json
from ..util import load_json, log, probe, run

RISKY_PHRASES = [
    "guaranteed return", "guaranteed profit", "get rich quick", "100% cure", "miracle cure",
    "click here", "download now", "free money", "©", "all rights reserved", "lyrics",
]

SYSTEM = """You are the Compliance & Fact QA reviewer of a YouTube channel. Review the script and metadata.
Check:
1. FACTS: flag any claim not supported by the fact sheet, or that may be wrong/outdated.
2. COPYRIGHT: copied lyrics, text, quotes or scripts; trademarked characters; brand misuse.
3. YOUTUBE POLICY: misinformation, medical or financial advice, dangerous/harmful content, hate or harassment,
   sensitive events, graphic content, spam or deceptive metadata (title/description must match the video), misleading clickbait.
4. DEFAMATION of real named people.
5. ORIGINALITY: must feel like a genuine, useful explainer, not filler or a reused template.
Return JSON: {"verdict": "pass"|"fail", "risk": "low"|"medium"|"high",
"issues": [{"category": str, "detail": str, "fix": str}]}
Fail if anything could cause a strike, demonetisation, or spread false info. Do not fail for harmless style preferences."""


def _mean_volume(path: str) -> float | None:
    p = run([S.ffmpeg, "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"], check=False)
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", p.stderr)
    return float(m.group(1)) if m else None


def technical(render: dict, script: dict, seo: dict, assets: list[dict]) -> list[str]:
    issues = []
    path = render["path"]
    info = probe(path)
    dur = float(info["format"]["duration"])
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)

    if dur > S.max_seconds:
        over = dur - S.max_seconds
        cut_words = int(over * (2.3 if S.language == "hi" else 2.6)) + 5
        issues.append(f"Video is {dur:.0f}s but max is {S.max_seconds}s. Shorten the narration by about {cut_words} words.")
    if dur < 15:
        issues.append(f"Video is only {dur:.0f}s. Add a little more explanation (target {S.target_seconds}s).")
    if not v or (v["width"], v["height"]) != (1080, 1920):
        issues.append("Video is not 1080x1920 vertical.")
    if not a:
        issues.append("Video has no audio track.")
    else:
        mv = _mean_volume(path)
        if mv is not None and mv < -40:
            issues.append(f"Audio is almost silent (mean {mv} dB).")
    if Path(path).stat().st_size > 200 * 1024 * 1024:
        issues.append("File larger than 200 MB.")

    t = seo.get("title", "")
    if not (5 <= len(t) <= 100):
        issues.append("Title length must be 5-100 characters.")
    if len(seo.get("description", "")) > 4800:
        issues.append("Description too long.")
    if sum(len(x) + 1 for x in seo.get("tags", [])) > 500:
        issues.append("Tags exceed 500 characters.")

    blob = (script["full_text"] + " " + t + " " + seo.get("description", "")).lower()
    for ph in RISKY_PHRASES:
        if ph in blob:
            issues.append(f"Risky phrase found: '{ph}'. Rewrite without it.")

    for asset in assets:
        if not asset.get("license"):
            issues.append(f"Asset without license record: {asset.get('path')}")

    history = load_json(DATA / "history.json", []) or []
    for h in history[-30:]:
        if SequenceMatcher(None, script["full_text"], h.get("script_text", "")).ratio() > 0.6:
            issues.append("Script is too similar to a previously published video (repetitive content). Make it clearly different.")
            break
    return issues


def review(render: dict, script: dict, seo: dict, facts: dict, assets: list[dict]) -> dict:
    tech = technical(render, script, seo, assets)
    user = json.dumps(
        {
            "script": script["full_text"],
            "title": seo["title"],
            "description": seo["description"],
            "fact_sheet": facts,
            "visual_queries": [a.get("query") for a in assets],
        },
        ensure_ascii=False,
    )
    llm = ask_json(SYSTEM, user, max_tokens=1500)
    llm_ok = llm.get("verdict") == "pass" and llm.get("risk") in ("low", "medium")

    fb = list(tech)
    for i in llm.get("issues", []):
        fb.append(f"[{i.get('category')}] {i.get('detail')} -> {i.get('fix')}")
    passed = not tech and llm_ok
    report = {
        "pass": passed,
        "technical_issues": tech,
        "llm_review": llm,
        "feedback": "\n".join(fb),
    }
    log("QA", "PASSED" if passed else "REJECTED:\n  " + "\n  ".join(fb))
    return report
