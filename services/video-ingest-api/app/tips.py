from sqlalchemy import Select, case, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import VideoRound


def select_tip_rounds(db: Session, match_ids: list[str], limit: int) -> list[VideoRound]:
    stmt: Select[tuple[VideoRound]] = select(VideoRound)
    if match_ids:
        stmt = stmt.where(VideoRound.match_id.in_(match_ids))
    stmt = stmt.order_by(
        case((VideoRound.highlight.is_(True), 0), else_=1),
        VideoRound.updated_at.desc(),
    ).limit(min(limit, settings.tip_context_limit))
    return list(db.scalars(stmt).all())


def build_tip_prompt(rounds: list[VideoRound]) -> str:
    context_blocks: list[str] = []
    for item in rounds:
        title = f"Round {item.round_index}"
        if item.highlight:
            title += " (highlight)"
        context_blocks.append(
            "\n".join(
                [
                    f"- {title}",
                    f"  lessons_learned: {item.lessons_learned or '(none)'}",
                    f"  emotional_log: {item.emotional_log or '(none)'}",
                ]
            )
        )

    joined = "\n".join(context_blocks) or "(no context)"
    return f"""あなたは Valorant の振り返りコーチです。
以下のラウンドメモだけを根拠に、最近の傾向と次の練習で試すべき改善案を日本語で短く具体的に返してください。

条件:
- 根拠が弱い断定はしない
- 出力は 3 セクション: 「傾向」「良い点」「次の1〜3個のTip」
- メモ内にない事実を作らない

ラウンドメモ:
{joined}
"""
