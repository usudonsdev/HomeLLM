from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Experience, Tag


def find_experiences(db: Session, keywords: list[str], limit: int | None = None) -> list[Experience]:
    max_n = limit or settings.rag_max_experiences
    cleaned = [k.strip() for k in keywords if k and k.strip()]
    if not cleaned:
        return list(db.scalars(select(Experience).order_by(Experience.created_at.desc()).limit(max_n)))

    tag_matches = select(Experience.id).join(Experience.tags).where(Tag.name.in_(cleaned))
    text_filters = []
    for keyword in cleaned:
        pattern = f"%{keyword}%"
        text_filters.extend(
            [
                Experience.emotional_log.ilike(pattern),
                Experience.lessons_learned.ilike(pattern),
                Experience.title.ilike(pattern),
                Experience.description.ilike(pattern),
            ]
        )

    stmt = (
        select(Experience)
        .where(or_(Experience.id.in_(tag_matches), *text_filters))
        .order_by(Experience.created_at.desc())
        .limit(max_n)
    )
    return list(db.scalars(stmt).unique())


def build_prompt(query: str, experiences: list[Experience]) -> str:
    blocks: list[str] = []
    for exp in experiences:
        blocks.append(
            "\n".join(
                [
                    f"## {exp.title}",
                    f"category: {exp.category}",
                    f"lessons_learned:\n{exp.lessons_learned or '(なし)'}",
                    f"emotional_log:\n{exp.emotional_log or '(なし)'}",
                ]
            )
        )
    context = "\n\n".join(blocks) if blocks else "(該当する経験ログなし)"
    return (
        "あなたは就活面接の自己分析を支援するアシスタントです。"
        "以下の経験ログだけを根拠に、泥臭い具体性を残したまま日本語で答えてください。"
        "ログにない事実は作らないでください。\n\n"
        f"# 経験ログ\n{context}\n\n"
        f"# 質問\n{query}\n"
    )
