"""Valorant segmenter Job.

Cut detection priority:
1. OpenCV template match against /media/templates/valorant/*.png (inter-round logos)
2. Transition spike detection (bright/flat overlays + large frame deltas)
3. Stub interval (SEGMENT_FALLBACK_SECONDS) if nothing usable is found
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ffprobe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def stub_cuts(duration: float, step: float) -> list[float]:
    if duration <= 0:
        return [0.0]
    cuts = [0.0]
    t = step
    while t < duration - 0.25:
        cuts.append(round(t, 3))
        t += step
    return cuts


def write_state(media_root: Path, job_id: str, **fields: object) -> None:
    state_dir = media_root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / f"{job_id}.json"
    current: dict = {}
    if path.exists():
        current = json.loads(path.read_text(encoding="utf-8"))
    current.update(fields)
    current["id"] = job_id
    current["updated_at"] = utc_now()
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")


def load_templates(template_dir: Path) -> list[tuple[str, np.ndarray]]:
    if not template_dir.is_dir():
        return []
    loaded: list[tuple[str, np.ndarray]] = []
    for path in sorted(template_dir.glob("*")):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None or img.size == 0:
            continue
        loaded.append((path.name, img))
    return loaded


def sample_grayscale_frames(
    source: Path,
    sample_every_seconds: float,
    max_width: int = 640,
) -> list[tuple[float, np.ndarray]]:
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {source}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, int(round(fps * sample_every_seconds)))
    samples: list[tuple[float, np.ndarray]] = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape[:2]
            if w > max_width:
                scale = max_width / float(w)
                gray = cv2.resize(gray, (max_width, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
            t = idx / fps if fps > 0 else float(idx)
            samples.append((round(t, 3), gray))
        idx += 1
        if frame_count and idx > frame_count + 10:
            break
    cap.release()
    return samples


def template_hits(
    samples: list[tuple[float, np.ndarray]],
    templates: list[tuple[str, np.ndarray]],
    threshold: float,
) -> list[tuple[float, str, float]]:
    hits: list[tuple[float, str, float]] = []
    for t, frame in samples:
        for name, tmpl in templates:
            th, tw = tmpl.shape[:2]
            fh, fw = frame.shape[:2]
            if th > fh or tw > fw:
                # Scale template down to fit frame width.
                scale = min(fw / float(tw), fh / float(th), 1.0)
                resized = cv2.resize(
                    tmpl,
                    (max(8, int(tw * scale)), max(8, int(th * scale))),
                    interpolation=cv2.INTER_AREA,
                )
            else:
                resized = tmpl
            result = cv2.matchTemplate(frame, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if float(max_val) >= threshold:
                hits.append((t, name, float(max_val)))
    return hits


def transition_hits(
    samples: list[tuple[float, np.ndarray]],
    brightness_floor: float = 180.0,
    variance_ceiling: float = 900.0,
    diff_floor: float = 45.0,
) -> list[tuple[float, str, float]]:
    """Detect logo-like overlays: bright/flat frames or sudden scene changes."""
    hits: list[tuple[float, str, float]] = []
    prev: np.ndarray | None = None
    for t, frame in samples:
        mean = float(np.mean(frame))
        var = float(np.var(frame))
        score = 0.0
        label = ""
        if mean >= brightness_floor and var <= variance_ceiling:
            score = mean / 255.0
            label = "bright_flat"
        if prev is not None:
            diff = float(np.mean(cv2.absdiff(frame, prev)))
            if diff >= diff_floor:
                # Prefer large jumps; combine with flatness bonus.
                jump_score = min(1.0, diff / 80.0)
                if jump_score > score:
                    score = jump_score
                    label = "scene_jump"
        if score > 0 and label:
            hits.append((t, label, score))
        prev = frame
    return hits


def merge_cut_times(
    duration: float,
    hits: list[tuple[float, str, float]],
    min_gap_seconds: float,
) -> list[float]:
    ordered = sorted(hits, key=lambda item: (-item[2], item[0]))
    chosen: list[float] = []
    for t, _name, _score in ordered:
        if t < 1.0 or t > duration - 1.0:
            continue
        if any(abs(t - c) < min_gap_seconds for c in chosen):
            continue
        chosen.append(t)
    cuts = [0.0] + sorted(round(t, 3) for t in chosen)
    # Drop near-duplicates after sort.
    cleaned = [cuts[0]]
    for t in cuts[1:]:
        if t - cleaned[-1] >= min_gap_seconds:
            cleaned.append(t)
    return cleaned


def detect_cuts(
    source: Path,
    duration: float,
    template_dir: Path,
    sample_every_seconds: float,
    template_threshold: float,
    min_gap_seconds: float,
    fallback_seconds: float,
) -> tuple[list[float], dict]:
    samples = sample_grayscale_frames(source, sample_every_seconds)
    templates = load_templates(template_dir)
    meta: dict = {
        "sample_every_seconds": sample_every_seconds,
        "sample_count": len(samples),
        "template_dir": str(template_dir),
        "template_count": len(templates),
        "template_threshold": template_threshold,
        "min_gap_seconds": min_gap_seconds,
    }

    if templates:
        hits = template_hits(samples, templates, template_threshold)
        cuts = merge_cut_times(duration, hits, min_gap_seconds)
        meta["method"] = "logo_template"
        meta["raw_hit_count"] = len(hits)
        meta["top_hits"] = [
            {"t": t, "template": name, "score": round(score, 4)}
            for t, name, score in sorted(hits, key=lambda x: -x[2])[:20]
        ]
        if len(cuts) >= 2:
            return cuts, meta

    hits = transition_hits(samples)
    cuts = merge_cut_times(duration, hits, min_gap_seconds)
    meta["method"] = "transition_spike"
    meta["raw_hit_count"] = len(hits)
    meta["top_hits"] = [
        {"t": t, "kind": name, "score": round(score, 4)}
        for t, name, score in sorted(hits, key=lambda x: -x[2])[:20]
    ]
    if len(cuts) >= 2:
        return cuts, meta

    cuts = stub_cuts(duration, fallback_seconds)
    meta["method"] = "stub_interval_fallback"
    meta["fallback_seconds"] = fallback_seconds
    meta["note"] = (
        "No logo/transition cuts found. "
        "Add PNGs under Documents/HomeLLM/videos/templates/valorant/ for logo matching."
    )
    return cuts, meta


def split_rounds(source: Path, cuts: list[float], duration: float, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ends = cuts[1:] + [duration]
    outputs: list[str] = []
    for idx, (start, end) in enumerate(zip(cuts, ends, strict=True), start=1):
        length = max(0.1, end - start)
        dest = out_dir / f"round_{idx:03d}.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start),
            "-i",
            str(source),
            "-t",
            str(length),
            "-c",
            "copy",
            str(dest),
        ]
        subprocess.check_call(cmd)
        outputs.append(str(dest))
    return outputs


def main() -> int:
    job_id = os.environ["JOB_ID"]
    source = Path(os.environ["SOURCE_PATH"])
    media_root = Path(os.environ.get("MEDIA_ROOT", "/media"))
    template_dir = Path(os.environ.get("LOGO_TEMPLATE_DIR", str(media_root / "templates" / "valorant")))
    sample_every = float(os.environ.get("SAMPLE_EVERY_SECONDS", "0.5"))
    template_threshold = float(os.environ.get("LOGO_MATCH_THRESHOLD", "0.72"))
    min_gap = float(os.environ.get("MIN_ROUND_GAP_SECONDS", "12"))
    fallback = float(os.environ.get("SEGMENT_FALLBACK_SECONDS", os.environ.get("STUB_SEGMENT_SECONDS", "90")))

    rounds_dir = media_root / "rounds" / job_id
    try:
        if not source.is_file():
            raise FileNotFoundError(f"source missing: {source}")

        write_state(media_root, job_id, status="segmenting", error=None)

        duration = ffprobe_duration(source)
        cuts, detect_meta = detect_cuts(
            source=source,
            duration=duration,
            template_dir=template_dir,
            sample_every_seconds=sample_every,
            template_threshold=template_threshold,
            min_gap_seconds=min_gap,
            fallback_seconds=fallback,
        )
        cuts_path = rounds_dir / "cuts.json"
        rounds_dir.mkdir(parents=True, exist_ok=True)
        cuts_path.write_text(
            json.dumps(
                {
                    "job_id": job_id,
                    "duration": duration,
                    "cuts_seconds": cuts,
                    "detection": detect_meta,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        outputs = split_rounds(source, cuts, duration, rounds_dir)
        write_state(
            media_root,
            job_id,
            status="ready",
            rounds_dir=str(rounds_dir),
            round_count=len(outputs),
            rounds=outputs,
            cuts_path=str(cuts_path),
            segment_method=detect_meta.get("method"),
            error=None,
        )
        print(
            f"segmented job={job_id} rounds={len(outputs)} method={detect_meta.get('method')}",
            flush=True,
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        write_state(media_root, job_id, status="failed", error=str(exc))
        print(f"segmenter failed: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
