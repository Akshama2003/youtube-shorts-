"""Orchestrator: runs the whole team, with a QA -> rewrite loop."""
from datetime import datetime
from pathlib import Path

from .agents import editor, publisher, qa, researcher, scout, seo, visuals, voice, writer
from .config import DATA, OUTPUT, S
from .util import load_json, log, save_json, slugify


def _remember(pick: dict, script: dict, seo_meta: dict, result: dict) -> None:
    hist = load_json(DATA / "history.json", []) or []
    hist.append(
        {
            "date": datetime.now().isoformat(timespec="seconds"),
            "topic": pick.get("topic"),
            "title": seo_meta.get("title"),
            "script_text": script["full_text"],
            "status": result["status"],
            "video_id": result.get("video_id", ""),
        }
    )
    save_json(DATA / "history.json", hist)


def run_one(topic: str | None = None, publish: bool = True) -> dict:
    log("Studio", "=" * 50)
    pick = scout.pick_topic(topic)
    job_dir = OUTPUT / f"{datetime.now():%Y%m%d-%H%M%S}-{slugify(str(pick.get('topic', 'video')))}"
    job_dir.mkdir(parents=True, exist_ok=True)
    save_json(job_dir / "pick.json", pick)

    facts = researcher.research(pick)
    save_json(job_dir / "facts.json", facts)

    feedback = ""
    script = seo_meta = report = None
    for attempt in range(S.max_revisions + 1):
        log("Studio", f"Production attempt {attempt + 1}/{S.max_revisions + 1}")
        script = writer.write(pick, facts, feedback)
        save_json(job_dir / "script.json", script)

        seo_meta = seo.make(pick, script)
        narration = voice.narrate(script, job_dir / "audio")
        assets = visuals.gather(script, job_dir / "assets")
        seo_meta = seo.add_credits(seo_meta, assets)
        render = editor.render(job_dir, narration, assets)

        save_json(job_dir / "seo.json", seo_meta)
        save_json(job_dir / "assets.json", assets)
        save_json(job_dir / "narration.json", narration)

        report = qa.review(render, script, seo_meta, facts, assets)
        save_json(job_dir / "qa.json", report)
        if report["pass"]:
            break
        feedback = report["feedback"]

    result = {"job_dir": str(job_dir), "status": "rejected", "title": seo_meta["title"]}
    if report["pass"]:
        if publish and S.auto_publish:
            try:
                result.update(publisher.upload(render["path"], seo_meta))
                result["status"] = "published"
            except Exception as e:
                result.update(status="ready", error=str(e))
                log("Publisher", f"Upload failed: {e}")
        else:
            result["status"] = "ready"
            log("Studio", f"Video approved. Publish later with: python main.py publish \"{job_dir}\"")
    else:
        log("Studio", "QA rejected every attempt. Nothing was published. See qa.json in the job folder.")

    save_json(job_dir / "result.json", result)
    _remember(pick, script, seo_meta, result)
    log("Studio", f"Status: {result['status']}  |  Folder: {job_dir}")
    return result


def publish_existing(job_dir: Path) -> dict:
    job_dir = Path(job_dir)
    seo_meta = load_json(job_dir / "seo.json")
    report = load_json(job_dir / "qa.json")
    if not seo_meta or not (job_dir / "final.mp4").exists():
        raise RuntimeError("That folder has no final.mp4 / seo.json")
    if not report or not report.get("pass"):
        raise RuntimeError("QA did not pass for this video. Refusing to publish.")
    res = publisher.upload(str(job_dir / "final.mp4"), seo_meta)
    res.update(job_dir=str(job_dir), status="published", title=seo_meta["title"])
    save_json(job_dir / "result.json", res)
    return res
