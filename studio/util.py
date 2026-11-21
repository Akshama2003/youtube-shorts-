import json
import re
import subprocess
import unicodedata
from pathlib import Path

from .config import S


def log(role: str, msg: str) -> None:
    print(f"[{role}] {msg}", flush=True)


def slugify(s: str, n: int = 40) -> str:
    a = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", a).strip("-").lower()[:n] or "video"


def run(cmd: list, cwd=None, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(
        [str(c) for c in cmd],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(map(str, cmd))}\n{p.stderr[-2000:]}")
    return p


def probe(path) -> dict:
    p = run([S.ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    return json.loads(p.stdout)


def duration(path) -> float:
    return float(probe(path)["format"]["duration"])


def load_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
