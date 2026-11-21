import argparse
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Hindi text in Windows consoles
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from studio.config import ROOT, S  # noqa: E402


def doctor() -> None:
    def row(ok, name, hint=""):
        print(f"  [{'OK' if ok else '!!'}] {name}" + (f"  -> {hint}" if not ok and hint else ""))

    print(f"Python {sys.version.split()[0]}")
    row(sys.version_info >= (3, 10), "Python 3.10+", "install Python 3.10 or newer")
    row(shutil.which(S.ffmpeg) is not None, "ffmpeg on PATH", "winget install Gyan.FFmpeg, then reopen PowerShell")
    row(shutil.which(S.ffprobe) is not None, "ffprobe on PATH", "comes with ffmpeg")
    if S.llm_provider == "gemini":
        row(bool(S.gemini_key), f"GEMINI_API_KEY (model {S.gemini_model})", "free key: https://aistudio.google.com/apikey")
    else:
        row(bool(S.anthropic_key), "ANTHROPIC_API_KEY", "add it to .env")
    row(bool(S.pexels_key or S.pixabay_key), "PEXELS_API_KEY or PIXABAY_API_KEY (optional)", "without one, only Wikimedia public-domain images + generated cards are used")
    row((ROOT / "client_secret.json").exists(), "client_secret.json (YouTube)", "see README: YouTube API setup")
    row((ROOT / "token.json").exists(), "token.json (run: python main.py auth)", "run: python main.py auth")
    print(f"\nAI={S.llm_provider}  Language={S.language}  Voice={S.voice_name}  Geo={S.geo}  Privacy={S.privacy}  AutoPublish={S.auto_publish}")


def main() -> None:
    ap = argparse.ArgumentParser(description="YouTube Shorts Studio - AI explainer video team")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="make (and publish) videos")
    r.add_argument("--count", type=int, default=1)
    r.add_argument("--topic", default=None, help="skip trend scouting and use this topic")
    r.add_argument("--no-publish", action="store_true", help="make + QA only, do not upload")

    p = sub.add_parser("publish", help="upload an already-approved job folder")
    p.add_argument("job_dir")

    sub.add_parser("trends", help="show today's trends")
    sub.add_parser("auth", help="log in to YouTube once")
    sub.add_parser("doctor", help="check your setup")

    a = ap.parse_args()

    if a.cmd == "doctor":
        doctor()
    elif a.cmd == "trends":
        from studio.agents.scout import fetch_trends

        for i, t in enumerate(fetch_trends(), 1):
            print(f"{i:2d}. {t['title']}  ({t['traffic']})")
    elif a.cmd == "auth":
        from studio.agents.publisher import authorize

        authorize()
    elif a.cmd == "publish":
        from studio.pipeline import publish_existing

        print(publish_existing(Path(a.job_dir)))
    elif a.cmd == "run":
        from studio.pipeline import run_one

        for n in range(a.count):
            print(f"\n######## VIDEO {n + 1}/{a.count} ########")
            try:
                run_one(a.topic, publish=not a.no_publish)
            except Exception as e:
                print(f"[Studio] Video {n + 1} failed: {e}")


if __name__ == "__main__":
    main()
