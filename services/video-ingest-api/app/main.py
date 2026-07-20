from __future__ import annotations

import asyncio
import re
import shutil
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import k8s_jobs, ollama_client, store
from app.config import settings
from app.db import get_db
from app.models import VideoMatch, VideoRound
from app.schemas import (
    VideoMatchDetailRead,
    VideoMatchIngest,
    VideoMatchSummaryRead,
    VideoRoundPatch,
    VideoRoundRead,
    VideoTipsRequest,
    VideoTipsResponse,
)
from app.store import JobStatus
from app.tips import build_tip_prompt, select_tip_rounds

ALLOWED_UPLOAD_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov"}

app = FastAPI(title="HomeLLM video-ingest API", version="0.1.0")
poller_task: asyncio.Task[None] | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateJobRequest(BaseModel):
    game: str = Field(pattern="^(valorant)$")
    filename: str = Field(
        min_length=1,
        description=r"Basename under Documents\HomeLLM\videos\inbox (or MEDIA_ROOT/inbox)",
    )


class JobResponse(BaseModel):
    id: str
    game: str
    filename: str
    status: JobStatus
    source_path: str | None = None
    rounds_dir: str | None = None
    k8s_job: str | None = None
    error: str | None = None
    round_count: int | None = None
    rounds: list[str] | None = None
    cuts_path: str | None = None
    analysis_status: str | None = None
    analyzer_job: str | None = None
    match_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class InboxFile(BaseModel):
    filename: str
    size_bytes: int


def _to_response(data: dict) -> JobResponse:
    return JobResponse(
        id=data["id"],
        game=data.get("game", "valorant"),
        filename=data.get("filename", ""),
        status=JobStatus(data.get("status", "queued")),
        source_path=data.get("source_path"),
        rounds_dir=data.get("rounds_dir"),
        k8s_job=data.get("k8s_job"),
        error=data.get("error"),
        round_count=data.get("round_count"),
        rounds=data.get("rounds"),
        cuts_path=data.get("cuts_path"),
        analysis_status=data.get("analysis_status"),
        analyzer_job=data.get("analyzer_job"),
        match_id=data.get("match_id"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


def _safe_basename(name: str) -> str:
    base = Path(name).name
    if not base or base != name:
        raise HTTPException(status_code=400, detail="filename must be a basename only")
    if re.search(r"[^\w.\- ()\[\]]", base):
        raise HTTPException(status_code=400, detail="filename has unsupported characters")
    return base


def _start_job_from_inbox(filename: str, game: str) -> dict:
    store.ensure_layout()
    source = store.inbox_dir() / filename
    if not source.is_file():
        raise HTTPException(status_code=404, detail=f"file not found in inbox: {filename}")

    job_id = store.new_job_id()
    work = store.work_dir(job_id)
    work.mkdir(parents=True, exist_ok=True)
    dest = work / f"source{source.suffix.lower() or '.mp4'}"
    shutil.move(str(source), str(dest))

    rounds = store.rounds_dir(job_id)
    rounds.mkdir(parents=True, exist_ok=True)

    created = store.utc_now()
    state = store.write_state(
        job_id,
        {
            "game": game,
            "filename": filename,
            "status": JobStatus.queued.value,
            "source_path": str(dest),
            "rounds_dir": str(rounds),
            "created_at": created,
            "k8s_job": None,
            "analysis_status": "pending",
            "analyzer_job": None,
            "match_id": None,
            "error": None,
        },
    )

    try:
        k8s_name = k8s_jobs.create_valorant_segment_job(job_id, str(dest))
        state = store.write_state(
            job_id,
            {
                **state,
                "status": JobStatus.segmenting.value,
                "k8s_job": k8s_name,
            },
        )
    except Exception as exc:  # noqa: BLE001
        state = store.write_state(
            job_id,
            {
                **state,
                "status": JobStatus.failed.value,
                "error": f"failed to create k8s Job: {exc}",
            },
        )
        raise HTTPException(status_code=502, detail=state["error"]) from exc

    return state


@app.on_event("startup")
async def startup() -> None:
    store.ensure_layout()
    global poller_task
    poller_task = asyncio.create_task(_analysis_poller())


@app.on_event("shutdown")
async def shutdown() -> None:
    global poller_task
    if poller_task is not None:
        poller_task.cancel()
        with suppress(asyncio.CancelledError):
            await poller_task
        poller_task = None


def _round_to_read(row: VideoRound) -> VideoRoundRead:
    return VideoRoundRead.model_validate(row)


def _match_to_summary(row: VideoMatch) -> VideoMatchSummaryRead:
    return VideoMatchSummaryRead(
        id=row.id,
        ingest_job_id=row.ingest_job_id,
        game=row.game,
        source_filename=row.source_filename,
        title=row.title,
        detail_analysis=row.detail_analysis,
        lessons_learned=row.lessons_learned,
        emotional_log=row.emotional_log,
        status=row.status,
        round_count=len(row.rounds),
        highlight_count=sum(1 for item in row.rounds if item.highlight),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _match_to_detail(row: VideoMatch) -> VideoMatchDetailRead:
    summary = _match_to_summary(row)
    return VideoMatchDetailRead(**summary.model_dump(), rounds=[_round_to_read(item) for item in row.rounds])


async def _analysis_poller() -> None:
    while True:
        for item in store.list_ready_for_analysis(stale_queued_seconds=settings.analyzer_stale_seconds):
            try:
                analyzer_name = k8s_jobs.create_valorant_analyzer_job(item["id"])
                store.write_state(
                    item["id"],
                    {
                        **item,
                        "analysis_status": "queued",
                        "analyzer_job": analyzer_name,
                        "error": None,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                store.write_state(
                    item["id"],
                    {
                        **item,
                        "analysis_status": "failed",
                        "error": f"failed to create analyzer Job: {exc}",
                    },
                )
        await asyncio.sleep(settings.analyzer_poll_seconds)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    store.ensure_layout()
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "service": "video-ingest-api",
        "media_root": settings.media_root,
        "inbox_exists": store.inbox_dir().exists(),
        "host_inbox_hint": settings.host_inbox_hint,
        "upload_max_bytes": settings.upload_max_bytes,
        "ollama_model": settings.ollama_model,
    }


@app.get("/v1/inbox", response_model=list[InboxFile])
def list_inbox() -> list[InboxFile]:
    store.ensure_layout()
    files: list[InboxFile] = []
    for path in sorted(store.inbox_dir().iterdir()):
        if path.is_file() and path.suffix.lower() in ALLOWED_UPLOAD_SUFFIXES:
            files.append(InboxFile(filename=path.name, size_bytes=path.stat().st_size))
    return files


@app.get("/v1/jobs", response_model=list[JobResponse])
def list_jobs() -> list[JobResponse]:
    return [_to_response(item) for item in store.list_states()]


@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    data = store.read_state(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _to_response(data)


@app.post("/v1/jobs/{job_id}/reanalyze", response_model=JobResponse)
def reanalyze_job(job_id: str) -> JobResponse:
    """Force a new analyzer Job for a ready ingest job (recovery from stuck queued)."""
    data = store.read_state(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="job not found")
    if data.get("status") != JobStatus.ready.value:
        raise HTTPException(status_code=409, detail="job must be ready before reanalyze")
    data = store.write_state(
        job_id,
        {
            **data,
            "analysis_status": "pending",
            "match_id": None,
            "error": None,
        },
    )
    try:
        analyzer_name = k8s_jobs.create_valorant_analyzer_job(job_id)
        data = store.write_state(
            job_id,
            {
                **data,
                "analysis_status": "queued",
                "analyzer_job": analyzer_name,
            },
        )
    except Exception as exc:  # noqa: BLE001
        data = store.write_state(
            job_id,
            {
                **data,
                "analysis_status": "failed",
                "error": f"failed to create analyzer Job: {exc}",
            },
        )
        raise HTTPException(status_code=502, detail=data["error"]) from exc
    return _to_response(data)


@app.post("/v1/jobs", response_model=JobResponse, status_code=201)
def create_job(payload: CreateJobRequest) -> JobResponse:
    filename = _safe_basename(payload.filename)
    return _to_response(_start_job_from_inbox(filename, payload.game))


@app.post("/v1/jobs/upload", response_model=JobResponse, status_code=201)
async def upload_and_create_job(
    file: UploadFile = File(...),
    game: str = Form("valorant"),
) -> JobResponse:
    """Demo / small-clip upload. Large VODs must be copied to the host inbox folder."""
    if game != "valorant":
        raise HTTPException(status_code=400, detail="only game=valorant is supported")

    raw_name = file.filename or "upload.mp4"
    filename = _safe_basename(raw_name)
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported extension {suffix or '(none)'}; allowed: {sorted(ALLOWED_UPLOAD_SUFFIXES)}",
        )

    store.ensure_layout()
    dest = store.inbox_dir() / filename
    if dest.exists():
        raise HTTPException(status_code=409, detail=f"inbox already has {filename}")

    written = 0
    try:
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > settings.upload_max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"file exceeds upload_max_bytes={settings.upload_max_bytes}. "
                            f"Copy large VODs to {settings.host_inbox_hint} instead."
                        ),
                    )
                out.write(chunk)
    except Exception:
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    if written == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="empty upload")

    return _to_response(_start_job_from_inbox(filename, game))


@app.get("/v1/matches", response_model=list[VideoMatchSummaryRead])
def list_matches(db: Session = Depends(get_db)) -> list[VideoMatchSummaryRead]:
    rows = db.scalars(select(VideoMatch).order_by(VideoMatch.created_at.desc())).all()
    return [_match_to_summary(row) for row in rows]


@app.get("/v1/matches/{match_id}", response_model=VideoMatchDetailRead)
def get_match(match_id: UUID, db: Session = Depends(get_db)) -> VideoMatchDetailRead:
    row = db.get(VideoMatch, match_id)
    if row is None:
        raise HTTPException(status_code=404, detail="match not found")
    return _match_to_detail(row)


@app.post("/internal/v1/matches", response_model=VideoMatchDetailRead, status_code=201)
def sink_match(payload: VideoMatchIngest, db: Session = Depends(get_db)) -> VideoMatchDetailRead:
    row = db.scalar(select(VideoMatch).where(VideoMatch.ingest_job_id == payload.ingest_job_id))
    if row is None:
        row = VideoMatch(
            ingest_job_id=payload.ingest_job_id,
            game=payload.game,
            source_filename=payload.source_filename,
            title=payload.title,
            detail_analysis=payload.detail_analysis,
            lessons_learned=payload.lessons_learned,
            emotional_log=payload.emotional_log,
            status=payload.status,
        )
        db.add(row)
        db.flush()
    else:
        row.game = payload.game
        row.source_filename = payload.source_filename
        row.title = payload.title
        row.detail_analysis = payload.detail_analysis
        row.lessons_learned = payload.lessons_learned
        row.emotional_log = payload.emotional_log
        row.status = payload.status
        row.rounds.clear()
        db.flush()

    for item in payload.rounds:
        row.rounds.append(
            VideoRound(
                round_index=item.round_index,
                clip_path=item.clip_path,
                facts=item.facts,
                lessons_learned=item.lessons_learned,
                emotional_log=item.emotional_log,
                highlight=item.highlight,
                highlight_reason=item.highlight_reason,
                keyframe_paths=item.keyframe_paths,
            )
        )

    db.commit()
    db.refresh(row)
    store_state = store.read_state(str(payload.ingest_job_id))
    if store_state is not None:
        store.write_state(
            str(payload.ingest_job_id),
            {
                **store_state,
                "analysis_status": "completed",
                "match_id": str(row.id),
                "error": None,
            },
        )
    return _match_to_detail(row)


@app.patch("/v1/rounds/{round_id}", response_model=VideoRoundRead)
def patch_round(round_id: UUID, payload: VideoRoundPatch, db: Session = Depends(get_db)) -> VideoRoundRead:
    row = db.get(VideoRound, round_id)
    if row is None:
        raise HTTPException(status_code=404, detail="round not found")
    row.highlight = payload.highlight
    row.highlight_reason = payload.highlight_reason
    db.commit()
    db.refresh(row)
    return _round_to_read(row)


@app.post("/v1/tips", response_model=VideoTipsResponse)
async def video_tips(payload: VideoTipsRequest, db: Session = Depends(get_db)) -> VideoTipsResponse:
    rounds = select_tip_rounds(db, [str(item) for item in payload.match_ids], payload.limit)
    prompt = build_tip_prompt(rounds)
    ollama = await ollama_client.check_ollama()

    titles = [f"{item.match.title} / Round {item.round_index}" for item in rounds]
    if not ollama["ok"]:
        return VideoTipsResponse(
            round_ids=[item.id for item in rounds],
            round_titles=titles,
            matched_count=len(rounds),
            answer=(
                "Ollama に接続できませんでした。ホストで Ollama が起動しているか、"
                f"OLLAMA_BASE_URL ({settings.ollama_base_url}) を確認してください。"
            ),
            model=settings.ollama_model,
            ollama_reachable=False,
        )

    try:
        answer = await ollama_client.generate(prompt)
    except Exception as exc:  # noqa: BLE001
        detail = str(exc).strip() or type(exc).__name__
        raise HTTPException(status_code=502, detail=f"Ollama generate failed: {detail}") from exc

    return VideoTipsResponse(
        round_ids=[item.id for item in rounds],
        round_titles=titles,
        matched_count=len(rounds),
        answer=answer,
        model=settings.ollama_model,
        ollama_reachable=True,
    )
