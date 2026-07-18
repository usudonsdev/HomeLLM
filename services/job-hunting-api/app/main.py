from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import ollama_client
from app.config import settings
from app.db import get_db
from app.models import Experience, Tag
from app.rag import build_prompt, find_experiences
from app.schemas import ExperienceCreate, ExperienceRead, RagRequest, RagResponse

app = FastAPI(title="HomeLLM job-hunting API (smoke)", version="0.1.0")


def to_read(exp: Experience) -> ExperienceRead:
    return ExperienceRead(
        id=exp.id,
        category=exp.category,
        title=exp.title,
        org_name=exp.org_name,
        start_date=exp.start_date,
        end_date=exp.end_date,
        description=exp.description,
        lessons_learned=exp.lessons_learned,
        emotional_log=exp.emotional_log,
        tags=[t.name for t in exp.tags],
        created_at=exp.created_at,
        updated_at=exp.updated_at,
    )


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "service": "job-hunting-api",
        "ollama_model": settings.ollama_model,
    }


@app.get("/health/ollama")
async def health_ollama() -> dict:
    result = await ollama_client.check_ollama()
    return {
        "ollama_base_url": settings.ollama_base_url,
        "configured_model": settings.ollama_model,
        **result,
    }


@app.get("/experiences", response_model=list[ExperienceRead])
def list_experiences(db: Session = Depends(get_db)) -> list[ExperienceRead]:
    rows = db.scalars(select(Experience).order_by(Experience.created_at.desc())).all()
    return [to_read(row) for row in rows]


@app.post("/experiences", response_model=ExperienceRead, status_code=201)
def create_experience(payload: ExperienceCreate, db: Session = Depends(get_db)) -> ExperienceRead:
    exp = Experience(
        category=payload.category,
        title=payload.title,
        org_name=payload.org_name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        description=payload.description,
        lessons_learned=payload.lessons_learned,
        emotional_log=payload.emotional_log,
    )
    for name in payload.tags:
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
        exp.tags.append(tag)

    db.add(exp)
    db.commit()
    db.refresh(exp)
    return to_read(exp)


@app.post("/rag/ask", response_model=RagResponse)
async def rag_ask(payload: RagRequest, db: Session = Depends(get_db)) -> RagResponse:
    keywords = payload.keywords or [payload.query]
    experiences = find_experiences(db, keywords)
    prompt = build_prompt(payload.query, experiences)
    ollama = await ollama_client.check_ollama()

    if not ollama["ok"]:
        return RagResponse(
            query=payload.query,
            matched_count=len(experiences),
            context_titles=[e.title for e in experiences],
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
        raise HTTPException(status_code=502, detail=f"Ollama generate failed: {exc}") from exc

    return RagResponse(
        query=payload.query,
        matched_count=len(experiences),
        context_titles=[e.title for e in experiences],
        answer=answer,
        model=settings.ollama_model,
        ollama_reachable=True,
    )
