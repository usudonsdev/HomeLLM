from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import k8s_jobs, store
from app.config import settings
from app.store import JobStatus

app = FastAPI(title="HomeLLM video-ingest API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateJobRequest(BaseModel):
    game: str = Field(pattern="^(valorant)$")
    filename: str = Field(min_length=1, description="Basename under media/inbox/")


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
    created_at: str | None = None
    updated_at: str | None = None


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
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


@app.on_event("startup")
def startup() -> None:
    store.ensure_layout()


@app.get("/health")
def health() -> dict:
    store.ensure_layout()
    return {
        "status": "ok",
        "service": "video-ingest-api",
        "media_root": settings.media_root,
        "inbox_exists": store.inbox_dir().exists(),
    }


@app.get("/v1/jobs", response_model=list[JobResponse])
def list_jobs() -> list[JobResponse]:
    return [_to_response(item) for item in store.list_states()]


@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    data = store.read_state(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _to_response(data)


@app.post("/v1/jobs", response_model=JobResponse, status_code=201)
def create_job(payload: CreateJobRequest) -> JobResponse:
    store.ensure_layout()
    filename = Path(payload.filename).name
    if filename != payload.filename or "/" in payload.filename or "\\" in payload.filename:
        raise HTTPException(status_code=400, detail="filename must be a basename only")

    source = store.inbox_dir() / filename
    if not source.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"file not found in inbox: {filename}",
        )

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
            "game": payload.game,
            "filename": filename,
            "status": JobStatus.queued.value,
            "source_path": str(dest),
            "rounds_dir": str(rounds),
            "created_at": created,
            "k8s_job": None,
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

    return _to_response(state)
