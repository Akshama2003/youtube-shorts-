"""Research Analyst: builds a verified fact sheet so the writer never invents facts."""
import json

from ..llm import ask_json
from ..util import log

SYSTEM = """You are the Research Analyst of a YouTube explainer studio.
Build a compact fact sheet for the topic. Rules:
- Include ONLY facts you are highly confident are true. For current events, rely ONLY on the news snippets provided.
- Do NOT invent statistics, dates, quotes, names or numbers. If unsure, leave it out.
- Prefer explanations of how/why (stable knowledge) over fragile numbers.
- List common misconceptions and things the video must avoid claiming.
Return JSON: {"summary": str, "facts": [{"claim": str, "basis": "news_snippet"|"well_established", "confidence": "high"|"medium"}],
"misconceptions": [str], "avoid": [str]}"""


def research(pick: dict) -> dict:
    facts = ask_json(SYSTEM, json.dumps(pick, ensure_ascii=False), max_tokens=2500)
    facts["facts"] = [f for f in facts.get("facts", []) if f.get("confidence") == "high"] or facts.get("facts", [])
    log("Researcher", f"Fact sheet ready: {len(facts['facts'])} facts")
    return facts
