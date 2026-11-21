"""Scriptwriter: writes the narration scene by scene."""
import json

from ..config import S
from ..llm import ask_json
from ..util import log

SYSTEM = """You are the Head Scriptwriter of a YouTube Shorts explainer studio.
Write a voice-over script for a {target}-second vertical explainer video in {lang}.
Rules:
- 100% original wording. Never quote lyrics, articles, books or other creators.
- Use ONLY facts from the fact sheet. Never invent statistics, quotes, dates or names.
- Scene 1 = a hook that creates curiosity within 2-3 seconds. Then explain step by step in simple words.
  Last scene = a satisfying takeaway plus a question that invites comments.
- Short punchy spoken sentences. No emojis, no hashtags, no stage directions, no markdown, no "like and subscribe" begging.
- Total narration about {words} words, split into {smin}-{smax} scenes (1-2 sentences each).
- For every scene give "visual_query": 2-4 English words for a concrete, filmable stock-footage subject
  (e.g. "rocket launch night", "city traffic aerial"). No people's names, no brands, no text/logos.
Return JSON: {{"hook": str, "scenes": [{{"narration": str, "visual_query": str}}]}}"""


def write(pick: dict, facts: dict, feedback: str = "") -> dict:
    words_per_sec = 2.3 if S.language == "hi" else 2.6
    system = SYSTEM.format(
        target=S.target_seconds,
        lang=S.lang_label,
        words=int(S.target_seconds * words_per_sec),
        smin=6,
        smax=9,
    )
    user = f"TOPIC:\n{json.dumps(pick, ensure_ascii=False)}\n\nFACT SHEET:\n{json.dumps(facts, ensure_ascii=False)}"
    if feedback:
        user += f"\n\nQA REJECTED THE PREVIOUS DRAFT. Fix all of this in the rewrite:\n{feedback}"
    script = ask_json(system, user, max_tokens=3000)
    scenes = [s for s in script.get("scenes", []) if s.get("narration", "").strip()]
    if len(scenes) < 3:
        raise RuntimeError("Writer returned too few scenes")
    script["scenes"] = scenes
    script["full_text"] = " ".join(s["narration"].strip() for s in scenes)
    n_words = len(script["full_text"].split())
    log("Scriptwriter", f"{len(scenes)} scenes, {n_words} words")
    return script
