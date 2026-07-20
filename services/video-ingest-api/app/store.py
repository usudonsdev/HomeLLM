from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from app.config import settings


class JobStatus(str, Enum):
    queued = "queued"
    segmenting = "segmenting"
    ready = "ready"
    failed = "failed"


def media_root() -> Path:
    return Path(settings.media_root)


def inbox_dir() -> Path:
    return media_root() / "inbox"


def work_dir(job_id: str) -> Path:
    return media_root() / "work" / job_id


def rounds_dir(job_id: str) -> Path:
    return media_root() / "rounds" / job_id


def state_path(job_id: str) -> Path:
    return media_root() / "state" / f"{job_id}.json"


def ensure_layout() -> None:
    for name in ("inbox", "work", "rounds", "state", "done", "failed"):
        (media_root() / name).mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_state(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_layout()
    path = state_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "id": job_id, "updated_at": utc_now()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def read_state(job_id: str) -> dict[str, Any] | None:
    path = state_path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_states() -> list[dict[str, Any]]:
    ensure_layout()
    states: list[dict[str, Any]] = []
    for path in sorted((media_root() / "state").glob("*.json")):
        states.append(json.loads(path.read_text(encoding="utf-8")))
    return states


def new_job_id() -> str:
    return str(uuid.uuid4())


def list_ready_for_analysis() -> list[dict[str, Any]]:
    ready_states: list[dict[str, Any]] = []
    for state in list_states():
        if state.get("status") != JobStatus.ready.value:
            continue
        if state.get("analysis_status") in {"queued", "running", "completed"}:
            continue
        ready_states.append(state)
    return ready_states
