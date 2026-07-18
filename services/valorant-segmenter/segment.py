"""Valorant segmenter Job entrypoint.

Phase A (current): stub cut points every STUB_SEGMENT_SECONDS.
Phase B: ffmpeg split into rounds/<jobId>/round_NNN.mp4
Later: replace stub cuts with OpenCV logo detection.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


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
    step = float(os.environ.get("STUB_SEGMENT_SECONDS", "2"))

    rounds_dir = media_root / "rounds" / job_id
    try:
        if not source.is_file():
            raise FileNotFoundError(f"source missing: {source}")

        write_state(
            media_root,
            job_id,
            status="segmenting",
            error=None,
        )

        duration = ffprobe_duration(source)
        cuts = stub_cuts(duration, step)
        cuts_path = rounds_dir / "cuts.json"
        rounds_dir.mkdir(parents=True, exist_ok=True)
        cuts_path.write_text(
            json.dumps(
                {
                    "job_id": job_id,
                    "method": "stub_interval",
                    "stub_segment_seconds": step,
                    "duration": duration,
                    "cuts_seconds": cuts,
                    "note": "Replace with Valorant inter-round logo detection later.",
                },
                indent=2,
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
            error=None,
        )
        print(f"segmented job={job_id} rounds={len(outputs)}", flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001
        write_state(
            media_root,
            job_id,
            status="failed",
            error=str(exc),
        )
        print(f"segmenter failed: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
