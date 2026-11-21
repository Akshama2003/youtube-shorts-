"""Voice Artist: narrates every scene with free Microsoft neural voices (edge-tts) and records word timings for subtitles."""
import asyncio
from pathlib import Path

import edge_tts

from ..config import S
from ..util import duration, log


async def _synth(text: str, mp3: Path) -> list[dict]:
    last = None
    for attempt in range(3):
        try:
            try:
                comm = edge_tts.Communicate(text, S.voice_name, rate=S.voice_rate, boundary="WordBoundary")
            except TypeError:  # older edge-tts
                comm = edge_tts.Communicate(text, S.voice_name, rate=S.voice_rate)
            words = []
            with open(mp3, "wb") as f:
                async for ch in comm.stream():
                    if ch["type"] == "audio":
                        f.write(ch["data"])
                    elif ch["type"] == "WordBoundary":
                        words.append(
                            {"text": ch["text"], "start": ch["offset"] / 1e7, "dur": ch["duration"] / 1e7}
                        )
            return words
        except Exception as e:
            last = e
            await asyncio.sleep(2)
    raise RuntimeError(f"Voice synthesis failed: {last}")


def even_words(text: str, dur: float) -> list[dict]:
    """Fallback word timing: spread words over the audio by length."""
    toks = text.split()
    weights = [len(t) + 1 for t in toks]
    total = sum(weights) or 1
    t0, out = 0.0, []
    for tok, w in zip(toks, weights):
        d = dur * 0.97 * w / total
        out.append({"text": tok, "start": t0, "dur": d})
        t0 += d
    return out


def narrate(script: dict, out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    res = []
    for i, sc in enumerate(script["scenes"]):
        text = sc["narration"].strip()
        mp3 = out_dir / f"scene_{i:02d}.mp3"
        words = asyncio.run(_synth(text, mp3))
        dur = duration(mp3)
        if len(words) < 0.5 * len(text.split()):
            words = even_words(text, dur)
        res.append({"text": text, "mp3": str(mp3), "duration": dur, "words": words})
    total = sum(r["duration"] for r in res)
    log("Voice Artist", f"Narration done with {S.voice_name}: {total:.1f}s")
    return res
