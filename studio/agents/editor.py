"""Video Editor: builds vertical 1080x1920 scenes, word-highlight subtitles (ASS), mixes audio, renders final.mp4."""
import math
import random
import shutil
from pathlib import Path

from ..config import ASSETS, S
from ..util import log, run

FPS = 30
PAD = 0.30  # seconds of breathing room after each scene


def _clip(asset: dict, dur: float, out: Path) -> None:
    common = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-an", "-r", str(FPS)]
    if asset["kind"] == "video":
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
        cmd = [S.ffmpeg, "-y", "-stream_loop", "-1", "-i", asset["path"], "-t", f"{dur:.3f}", "-vf", vf, *common, out]
    else:
        frames = int(round(dur * FPS))
        vf = (
            "scale=1296:2304:force_original_aspect_ratio=increase,crop=1296:2304,"
            "zoompan=z='min(zoom+0.0007,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s=1080x1920:fps={FPS},setsar=1"
        )
        cmd = [S.ffmpeg, "-y", "-i", asset["path"], "-vf", vf, "-frames:v", str(frames), *common, out]
    run(cmd)


def _ass_time(sec: float) -> str:
    cs = max(0, int(round(sec * 100)))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _chunks(words: list[dict], maxw: int = 3):
    cur = []
    for w in words:
        cur.append(w)
        if len(cur) >= maxw or w["text"].rstrip()[-1:] in ".?!,।":
            yield cur
            cur = []
    if cur:
        yield cur


def build_ass(narration: list[dict], scene_durs: list[float], path: Path) -> None:
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Main,{S.font},84,&H0000E5FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,2,2,60,60,520,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines, offset = [], 0.0
    for sc, sdur in zip(narration, scene_durs):
        chunks = list(_chunks(sc["words"]))
        for ci, ch in enumerate(chunks):
            start = offset + ch[0]["start"]
            nxt = offset + chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else offset + sdur
            end = min(nxt, offset + ch[-1]["start"] + ch[-1]["dur"] + 0.15)
            if end <= start:
                end = start + 0.3
            text = ""
            for j, w in enumerate(ch):
                nstart = ch[j + 1]["start"] if j + 1 < len(ch) else w["start"] + w["dur"]
                k = max(1, int(round((nstart - w["start"]) * 100)))
                word = w["text"].replace("{", "(").replace("}", ")").replace("\n", " ")
                if S.language != "hi":
                    word = word.upper()
                text += "{\\k%d}%s " % (k, word)
            lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Main,,0,0,0,,{text.strip()}")
        offset += sdur
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def _pick_music() -> Path | None:
    files = [p for p in (ASSETS / "music").glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a")]
    return random.choice(files) if files else None


def render(job_dir: Path, narration: list[dict], assets: list[dict]) -> dict:
    build = job_dir / "build"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)

    scene_durs = []
    vlist, alist = [], []
    for i, (n, a) in enumerate(zip(narration, assets)):
        dur = math.ceil((n["duration"] + PAD) * FPS) / FPS  # whole frames -> no drift
        scene_durs.append(dur)
        _clip(a, dur, build / f"v{i:02d}.mp4")
        run(
            [S.ffmpeg, "-y", "-i", n["mp3"], "-af", "apad", "-t", f"{dur:.3f}", "-ar", "44100", "-ac", "2",
             build / f"a{i:02d}.wav"]
        )
        vlist.append(f"file 'v{i:02d}.mp4'")
        alist.append(f"file 'a{i:02d}.wav'")

    (build / "v.txt").write_text("\n".join(vlist), encoding="utf-8")
    (build / "a.txt").write_text("\n".join(alist), encoding="utf-8")
    run([S.ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", "v.txt", "-c", "copy", "video_raw.mp4"], cwd=build)
    run([S.ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", "a.txt", "-c", "copy", "voice.wav"], cwd=build)
    build_ass(narration, scene_durs, build / "subs.ass")

    final = job_dir / "final.mp4"
    music = _pick_music()
    cmd = [S.ffmpeg, "-y", "-i", "video_raw.mp4", "-i", "voice.wav"]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        af = (
            "[2:a]volume=0.10[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0,volume=2,"
            "loudnorm=I=-16:TP=-1.5:LRA=11[a]"
        )
        log("Video Editor", f"Background music: {music.name} (make sure you hold the license for it)")
    else:
        af = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    fc = f"[0:v]ass=subs.ass[v];{af}"
    cmd += [
        "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", "-shortest", str(final),
    ]
    run(cmd, cwd=build)
    total = sum(scene_durs)
    log("Video Editor", f"Rendered {final.name}: {total:.1f}s")
    return {"path": str(final), "duration": total, "scene_durations": scene_durs, "music": music.name if music else ""}
