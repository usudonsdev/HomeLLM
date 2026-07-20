from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def round_duration_seconds(cuts: list[float], total_duration: float, index: int) -> float:
    start = cuts[index - 1]
    end = cuts[index] if index < len(cuts) else total_duration
    return max(0.1, round(end - start, 2))


def build_round_payload(round_index: int, clip_path: str, duration_seconds: float) -> dict:
    phase = "序盤" if round_index <= 3 else "中盤" if round_index <= 6 else "終盤"
    highlight = round_index == 1 or round_index % 3 == 0 or duration_seconds >= 3.0
    reason = None
    if highlight:
        reason = "見返し優先候補。展開が長いか、判断の癖を確認しやすいラウンド。"
    return {
        "round_index": round_index,
        "clip_path": clip_path,
        "facts": f"{phase}のラウンド候補。stub 分割クリップ長は約 {duration_seconds:.1f} 秒。",
        "lessons_learned": (
            "撃ち合い結果だけでなく、ラウンド開始直後の位置取りと情報取得の順番を確認する。"
            if round_index % 2 == 0
            else "有利不利が動いた瞬間の判断を短く言語化して、次ラウンドに持ち越さない。"
        ),
        "emotional_log": (
            "テンポが早い場面でも焦り過ぎず、次の行動理由を一言で言える状態を目指す。"
            if highlight
            else "落ち着いているが、漫然と流し見すると学びが薄くなりやすい。"
        ),
        "highlight": highlight,
        "highlight_reason": reason,
        "keyframe_paths": [],
    }


def build_match_payload(job_id: str, state: dict, cuts_meta: dict) -> dict:
    rounds = state.get("rounds") or []
    cuts = cuts_meta.get("cuts_seconds") or [0.0]
    total_duration = float(cuts_meta.get("duration") or 0.0)
    round_payloads: list[dict] = []
    highlight_indexes: list[int] = []
    for idx, clip_path in enumerate(rounds, start=1):
        duration_seconds = round_duration_seconds(cuts, total_duration, idx)
        payload = build_round_payload(idx, clip_path, duration_seconds)
        if payload["highlight"]:
            highlight_indexes.append(idx)
        round_payloads.append(payload)

    highlight_text = ", ".join(f"R{idx:02d}" for idx in highlight_indexes[:5]) or "なし"
    title = f"Valorant {Path(state.get('filename') or 'match').stem}"
    detail_analysis = (
        f"{len(round_payloads)} 個のクリップに分割された試合として整理しました。"
        f" 現在の analyzer は stub 分割ベースですが、見返し優先は {highlight_text} として保存しています。\n\n"
        "確認観点:\n"
        "1. ラウンド開始直後の立ち位置と索敵順\n"
        "2. 有利不利が変わった瞬間の判断\n"
        "3. 負けラウンド後に次へ引きずっていないか"
    )
    return {
        "ingest_job_id": job_id,
        "game": state.get("game", "valorant"),
        "source_filename": state.get("filename", "unknown.mp4"),
        "title": title,
        "detail_analysis": detail_analysis,
        "lessons_learned": "ハイライト優先で見返し、立ち位置・情報取得・判断切替の3点を短く振り返る。",
        "emotional_log": "良し悪しを感情だけで終わらせず、次の1ラウンドで試す行動に変換する。",
        "status": "analyzed",
        "rounds": round_payloads,
    }


def main() -> int:
    job_id = os.environ["JOB_ID"]
    media_root = Path(os.environ.get("MEDIA_ROOT", "/media"))
    api_base = os.environ.get("INTERNAL_API_BASE_URL", "http://video-ingest-api:8090").rstrip("/")

    state_path = media_root / "state" / f"{job_id}.json"
    state = read_json(state_path)
    cuts_path = Path(state["cuts_path"])
    cuts_meta = read_json(cuts_path)

    write_state(media_root, job_id, analysis_status="running", error=None)
    payload = build_match_payload(job_id, state, cuts_meta)

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{api_base}/internal/v1/matches", json=payload)
            response.raise_for_status()
            match_id = response.json().get("id")
    except Exception as exc:  # noqa: BLE001
        write_state(media_root, job_id, analysis_status="failed", error=str(exc))
        raise

    write_state(media_root, job_id, analysis_status="completed", match_id=match_id, error=None)
    print(f"analyzed job={job_id} match_id={match_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
