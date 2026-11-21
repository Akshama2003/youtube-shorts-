import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OUTPUT = ROOT / "output"
DATA = ROOT / "data"
ASSETS = ROOT / "assets"


def _s(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return default if v is None or v.strip() == "" else v.strip()


def _b(name: str, default: bool) -> bool:
    v = _s(name, "")
    return default if v == "" else v.lower() in ("1", "true", "yes", "y", "on")


def _i(name: str, default: int) -> int:
    try:
        return int(_s(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    anthropic_key: str = _s("ANTHROPIC_API_KEY")
    model: str = _s("CLAUDE_MODEL", "claude-sonnet-5-5")
    pexels_key: str = _s("PEXELS_API_KEY")
    language: str = _s("LANGUAGE", "hi").lower()
    geo: str = _s("GEO", "IN").upper()
    niche: str = _s("NICHE")
    channel_name: str = _s("CHANNEL_NAME")
    target_seconds: int = _i("TARGET_SECONDS", 45)
    max_seconds: int = _i("MAX_SECONDS", 58)
    voice: str = _s("VOICE")
    voice_rate: str = _s("VOICE_RATE", "+0%")
    max_revisions: int = _i("MAX_REVISIONS", 2)
    auto_publish: bool = _b("AUTO_PUBLISH", True)
    privacy: str = _s("YT_PRIVACY", "private").lower()
    disclose_ai: bool = _b("DISCLOSE_AI", True)
    sub_font: str = _s("SUB_FONT")
    ffmpeg: str = _s("FFMPEG", "ffmpeg")
    ffprobe: str = _s("FFPROBE", "ffprobe")

    @property
    def voice_name(self) -> str:
        if self.voice:
            return self.voice
        return "hi-IN-SwaraNeural" if self.language == "hi" else "en-IN-NeerjaNeural"

    @property
    def lang_label(self) -> str:
        if self.language == "hi":
            return "Hindi written in Devanagari script (simple, spoken, everyday Hindi)"
        return "clear, simple English"

    @property
    def font(self) -> str:
        if self.sub_font:
            return self.sub_font
        return "Nirmala UI" if self.language == "hi" else "Arial"


S = Settings()
