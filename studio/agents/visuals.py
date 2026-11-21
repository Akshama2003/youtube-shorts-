"""Visual Director: sources royalty-free footage (Pexels) and logs the license of every asset.
Falls back to self-generated gradient cards, which carry no third-party rights at all."""
import hashlib
import json
import textwrap
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from ..config import DATA, S
from ..util import log

PEXELS_LICENSE = "Pexels License (free for commercial use, attribution not required)"
PIXABAY_LICENSE = "Pixabay Content License (free for commercial use, attribution not required)"
PALETTES = [
    ((15, 32, 80), (120, 60, 200)),
    ((10, 70, 90), (20, 160, 140)),
    ((90, 20, 50), (230, 100, 60)),
    ((20, 20, 40), (60, 90, 160)),
]


def _get(url: str, params: dict) -> dict:
    r = requests.get(url, headers={"Authorization": S.pexels_key}, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _download(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def _pexels_video(query: str, dest: Path, used: set) -> dict | None:
    data = _get(
        "https://api.pexels.com/videos/search",
        {"query": query, "orientation": "portrait", "size": "medium", "per_page": 15},
    )
    for v in data.get("videos", []):
        if v["id"] in used:
            continue
        files = [
            f
            for f in v.get("video_files", [])
            if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height") and f["height"] >= f["width"]
        ]
        if not files:
            continue
        files.sort(key=lambda f: (f["width"] > 1080, abs(f["width"] - 1080)))
        _download(files[0]["link"], dest)
        used.add(v["id"])
        return {
            "path": str(dest),
            "kind": "video",
            "source": "pexels",
            "url": v.get("url", ""),
            "credit": (v.get("user") or {}).get("name", ""),
            "license": PEXELS_LICENSE,
        }
    return None


def _pexels_photo(query: str, dest: Path, used: set) -> dict | None:
    data = _get(
        "https://api.pexels.com/v1/search", {"query": query, "orientation": "portrait", "per_page": 15}
    )
    for p in data.get("photos", []):
        if ("p", p["id"]) in used:
            continue
        _download(p["src"].get("large2x") or p["src"]["large"], dest)
        used.add(("p", p["id"]))
        return {
            "path": str(dest),
            "kind": "image",
            "source": "pexels",
            "url": p.get("url", ""),
            "credit": p.get("photographer", ""),
            "license": PEXELS_LICENSE,
        }
    return None


_last_pix = 0.0


def _pix_get(url: str, params: dict) -> dict:
    """Pixabay GET with 24h disk cache, request spacing and wait-and-retry on 429."""
    global _last_pix
    ck = DATA / "cache" / (hashlib.md5((url + json.dumps(params, sort_keys=True)).encode()).hexdigest() + ".json")
    try:
        if ck.exists() and time.time() - ck.stat().st_mtime < 86400:
            return json.loads(ck.read_text(encoding="utf-8"))
    except Exception:
        pass
    for _ in range(3):
        gap = 1.0 - (time.time() - _last_pix)
        if gap > 0:
            time.sleep(gap)
        r = requests.get(url, params={**params, "key": S.pixabay_key}, timeout=30)
        _last_pix = time.time()
        if r.status_code == 429:
            try:
                reset = int(float(r.headers.get("X-RateLimit-Reset", "60")))
            except ValueError:
                reset = 60
            wait = min(max(reset, 10), 70)
            log("Visual Director", f"Pixabay rate limit hit - waiting {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        data = r.json()
        ck.parent.mkdir(parents=True, exist_ok=True)
        ck.write_text(json.dumps(data), encoding="utf-8")
        return data
    raise RuntimeError("Pixabay rate limit still exceeded; try again in a few minutes")


def _pixabay_video(query: str, dest: Path, used: set) -> dict | None:
    data = _pix_get("https://pixabay.com/api/videos/", {"q": query, "per_page": 20, "safesearch": "true"})
    for v in data.get("hits", []):
        if ("px", v["id"]) in used:
            continue
        vids = v.get("videos", {})
        f = next((vids[k] for k in ("large", "medium", "small") if vids.get(k, {}).get("url")), None)
        if not f:
            continue
        _download(f["url"], dest)
        used.add(("px", v["id"]))
        return {
            "path": str(dest), "kind": "video", "source": "pixabay",
            "url": v.get("pageURL", ""), "credit": v.get("user", ""), "license": PIXABAY_LICENSE,
        }
    return None


def _pixabay_photo(query: str, dest: Path, used: set) -> dict | None:
    data = _pix_get(
        "https://pixabay.com/api/",
        {"q": query, "image_type": "photo", "orientation": "vertical", "per_page": 20, "safesearch": "true"},
    )
    for p in data.get("hits", []):
        if ("pxp", p["id"]) in used:
            continue
        _download(p.get("largeImageURL") or p["webformatURL"], dest)
        used.add(("pxp", p["id"]))
        return {
            "path": str(dest), "kind": "image", "source": "pixabay",
            "url": p.get("pageURL", ""), "credit": p.get("user", ""), "license": PIXABAY_LICENSE,
        }
    return None


WIKI_LICENSE = "Public domain / CC0 (Wikimedia Commons)"
WIKI_UA = {"User-Agent": "yt-shorts-studio/1.0 (educational explainer videos)"}


def _wikimedia_photo(query: str, dest: Path, used: set) -> dict | None:
    """Keyless fallback. Only accepts files whose license metadata says Public domain or CC0."""
    r = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        headers=WIKI_UA,
        params={
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": 30, "prop": "imageinfo",
            "iiprop": "url|size|extmetadata", "iiurlwidth": 1600,
        },
        timeout=30,
    )
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages", {})
    for pg in sorted(pages.values(), key=lambda x: x.get("index", 0)):
        info = (pg.get("imageinfo") or [{}])[0]
        lic = ((info.get("extmetadata") or {}).get("LicenseShortName") or {}).get("value", "").lower()
        if not (lic.startswith("public domain") or lic.startswith("cc0") or lic.startswith("pd")):
            continue
        if ("w", pg["pageid"]) in used or info.get("height", 0) < 900 or info.get("width", 0) < 900:
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        _download_ua(url, dest)
        used.add(("w", pg["pageid"]))
        return {
            "path": str(dest), "kind": "image", "source": "wikimedia",
            "url": info.get("descriptionurl", ""), "credit": "", "license": WIKI_LICENSE,
        }
    return None


def _download_ua(url: str, dest: Path) -> None:
    with requests.get(url, headers=WIKI_UA, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def _font(size: int):
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_card(text: str, dest: Path, idx: int) -> dict:
    top, bot = PALETTES[idx % len(PALETTES)]
    w, h = 1080, 1920
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    f = _font(120)
    lines = textwrap.wrap(text.upper(), 12) or [""]
    line_h = 150
    y0 = h // 2 - (len(lines) * line_h) // 2 - 200
    for i, ln in enumerate(lines):
        bb = d.textbbox((0, 0), ln, font=f)
        d.text(((w - (bb[2] - bb[0])) / 2, y0 + i * line_h), ln, font=f, fill=(255, 255, 255))
    img.save(dest, quality=92)
    return {
        "path": str(dest),
        "kind": "image",
        "source": "generated",
        "url": "",
        "credit": "",
        "license": "Generated by this program (no third-party rights)",
    }


def gather(script: dict, out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    used: set = set()
    assets = []
    for i, sc in enumerate(script["scenes"]):
        q = sc.get("visual_query", "abstract background").strip()
        asset = None
        providers = []
        if S.pexels_key:
            providers.append(("Pexels", _pexels_video, _pexels_photo))
        if S.pixabay_key:
            providers.append(("Pixabay", _pixabay_video, _pixabay_photo))
        providers.append(("Wikimedia", lambda *a: None, _wikimedia_photo))
        for pname, vfn, pfn in providers:
            for tq in (q, " ".join(q.split()[:2])):
                try:
                    asset = vfn(tq, out_dir / f"scene_{i:02d}.mp4", used) or pfn(tq, out_dir / f"scene_{i:02d}.jpg", used)
                except Exception as e:
                    log("Visual Director", f"{pname} error for '{tq}': {e}")
                if asset:
                    break
            if asset:
                break
        if not asset:
            asset = make_card(q, out_dir / f"scene_{i:02d}.jpg", i)
        asset["query"] = q
        assets.append(asset)
    n_stock = sum(1 for a in assets if a["source"] != "generated")
    log("Visual Director", f"{n_stock} stock clips, {len(assets) - n_stock} generated cards")
    return assets
