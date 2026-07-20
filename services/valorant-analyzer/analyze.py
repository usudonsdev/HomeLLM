"""Valorant analyzer Job — Ollama-backed match/round notes + highlight flags."""

from __future__ import annotations

import json
import os
import re
import subprocess
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


def extract_keyframes_timed(clip_path: Path, duration: float, out_dir: Path, count: int = 3) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    if duration <= 0:
        duration = 1.0
    for i in range(count):
        t = max(0.05, min(duration - 0.05, duration * (i + 0.5) / count))
        dest = out_dir / f"kf_{i + 1:02d}.jpg"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{t:.3f}",
            "-i",
            str(clip_path),
            "-frames:v",
            "1",
            "-q:v",
            "4",
            str(dest),
        ]
        try:
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if dest.is_file() and dest.stat().st_size > 0:
                paths.append(str(dest))
        except subprocess.CalledProcessError:
            continue
    return paths


def ollama_generate(prompt: str, *, base_url: str, model: str, timeout: float, keep_alive: str) -> str:
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive,
        "format": "json",
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    answer = data.get("response")
    if answer is None:
        raise RuntimeError(f"Ollama response missing 'response': {str(data)[:400]}")
    return str(answer)


def parse_json_object(text: str) -> dict:
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object in model output: {text[:300]}")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("model JSON was not an object")
    return data


def analyze_round(
    *,
    round_index: int,
    duration_seconds: float,
    total_rounds: int,
    segment_method: str,
    keyframe_paths: list[str],
    ollama_base_url: str,
    model: str,
    timeout: float,
    keep_alive: str,
) -> dict:
    phase = "序盤" if round_index <= max(1, total_rounds // 3) else "中盤" if round_index <= max(2, 2 * total_rounds // 3) else "終盤"
    prompt = f"""あなたは Valorant の振り返りコーチです。
次のラウンドについて、日本語で JSON だけを返してください（説明文禁止）。

スキーマ:
{{
  "facts": "客観的な事実メモ（1〜3文）",
  "lessons_learned": "学び（1〜2文）",
  "emotional_log": "感情・メンタルの動き（1文）",
  "highlight": true/false,
  "highlight_reason": "highlight=true のとき理由。false なら空文字"
}}

条件:
- 映像ピクセルは直接見えない。与えられたメタデータだけを根拠にする。
- 断定しすぎない。推測は控えめに。
- highlight=true は学習価値が高い／見返し優先のときだけ。

メタデータ:
- round_index: {round_index}/{total_rounds}
- phase: {phase}
- clip_duration_seconds: {duration_seconds}
- segment_method: {segment_method}
- keyframe_count: {len(keyframe_paths)}
- keyframe_paths: {keyframe_paths}
"""
    raw = ollama_generate(prompt, base_url=ollama_base_url, model=model, timeout=timeout, keep_alive=keep_alive)
    data = parse_json_object(raw)
    highlight = bool(data.get("highlight", False))
    reason = str(data.get("highlight_reason") or "").strip() or None
    if not highlight:
        reason = None
    return {
        "facts": str(data.get("facts") or f"{phase}ラウンド。長さ約 {duration_seconds:.1f} 秒。").strip(),
        "lessons_learned": str(data.get("lessons_learned") or "開始直後の立ち位置と情報取得順を確認する。").strip(),
        "emotional_log": str(data.get("emotional_log") or "焦りと冷静さの切替を意識する。").strip(),
        "highlight": highlight,
        "highlight_reason": reason,
    }


def analyze_match(
    *,
    title: str,
    filename: str,
    segment_method: str,
    rounds: list[dict],
    ollama_base_url: str,
    model: str,
    timeout: float,
    keep_alive: str,
) -> dict:
    compact = []
    for item in rounds:
        compact.append(
            {
                "round_index": item["round_index"],
                "duration": item.get("_duration"),
                "highlight": item["highlight"],
                "facts": item["facts"],
                "lessons_learned": item["lessons_learned"],
                "emotional_log": item["emotional_log"],
            }
        )
    prompt = f"""あなたは Valorant の試合振り返りコーチです。
ラウンドメモを根拠に、試合全体の詳細振り返りを日本語 JSON だけで返してください。

スキーマ:
{{
  "detail_analysis": "試合全体の詳細分析（流れ・勝敗要因っぽい傾向・次試合への課題。短すぎない。3〜8文）",
  "lessons_learned": "試合全体の学び（2〜4文）",
  "emotional_log": "試合を通した感情・メンタル（1〜3文）"
}}

条件:
- ラウンドメモにない事実を捏造しない。
- 一般論だけで埋めない。与えたメモを引用・要約する。

試合:
- title: {title}
- source_filename: {filename}
- segment_method: {segment_method}
- rounds: {json.dumps(compact, ensure_ascii=False)}
"""
    raw = ollama_generate(prompt, base_url=ollama_base_url, model=model, timeout=timeout, keep_alive=keep_alive)
    data = parse_json_object(raw)
    return {
        "detail_analysis": str(data.get("detail_analysis") or "").strip(),
        "lessons_learned": str(data.get("lessons_learned") or "").strip() or None,
        "emotional_log": str(data.get("emotional_log") or "").strip() or None,
    }


def build_match_payload(
    job_id: str,
    state: dict,
    cuts_meta: dict,
    *,
    ollama_base_url: str,
    model: str,
    timeout: float,
    keep_alive: str,
    media_root: Path,
) -> dict:
    rounds = state.get("rounds") or []
    cuts = cuts_meta.get("cuts_seconds") or [0.0]
    total_duration = float(cuts_meta.get("duration") or 0.0)
    segment_method = str((cuts_meta.get("detection") or {}).get("method") or state.get("segment_method") or "unknown")
    title = f"Valorant {Path(state.get('filename') or 'match').stem}"

    round_payloads: list[dict] = []
    for idx, clip_path in enumerate(rounds, start=1):
        duration_seconds = round_duration_seconds(cuts, total_duration, idx)
        kf_dir = media_root / "rounds" / job_id / "keyframes" / f"round_{idx:03d}"
        keyframes = extract_keyframes_timed(Path(clip_path), duration_seconds, kf_dir, count=3)
        analyzed = analyze_round(
            round_index=idx,
            duration_seconds=duration_seconds,
            total_rounds=len(rounds),
            segment_method=segment_method,
            keyframe_paths=keyframes,
            ollama_base_url=ollama_base_url,
            model=model,
            timeout=timeout,
            keep_alive=keep_alive,
        )
        round_payloads.append(
            {
                "round_index": idx,
                "clip_path": clip_path,
                "facts": analyzed["facts"],
                "lessons_learned": analyzed["lessons_learned"],
                "emotional_log": analyzed["emotional_log"],
                "highlight": analyzed["highlight"],
                "highlight_reason": analyzed["highlight_reason"],
                "keyframe_paths": keyframes,
                "_duration": duration_seconds,
            }
        )

    match_notes = analyze_match(
        title=title,
        filename=str(state.get("filename") or "unknown.mp4"),
        segment_method=segment_method,
        rounds=round_payloads,
        ollama_base_url=ollama_base_url,
        model=model,
        timeout=timeout,
        keep_alive=keep_alive,
    )
    if not match_notes["detail_analysis"]:
        highlights = [f"R{item['round_index']:02d}" for item in round_payloads if item["highlight"]]
        match_notes["detail_analysis"] = (
            f"{len(round_payloads)} ラウンドに分割（method={segment_method}）。"
            f" ハイライト候補: {', '.join(highlights) or 'なし'}。"
        )

    for item in round_payloads:
        item.pop("_duration", None)

    return {
        "ingest_job_id": job_id,
        "game": state.get("game", "valorant"),
        "source_filename": state.get("filename", "unknown.mp4"),
        "title": title,
        "detail_analysis": match_notes["detail_analysis"],
        "lessons_learned": match_notes["lessons_learned"],
        "emotional_log": match_notes["emotional_log"],
        "status": "analyzed",
        "rounds": round_payloads,
    }


def main() -> int:
    job_id = os.environ["JOB_ID"]
    media_root = Path(os.environ.get("MEDIA_ROOT", "/media"))
    api_base = os.environ.get("INTERNAL_API_BASE_URL", "http://video-ingest-api:8090").rstrip("/")
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    model = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b")
    timeout = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "300"))
    keep_alive = os.environ.get("OLLAMA_KEEP_ALIVE", "24h")

    state_path = media_root / "state" / f"{job_id}.json"
    state = read_json(state_path)
    cuts_path = Path(state["cuts_path"])
    cuts_meta = read_json(cuts_path)

    write_state(media_root, job_id, analysis_status="running", error=None)
    try:
        payload = build_match_payload(
            job_id,
            state,
            cuts_meta,
            ollama_base_url=ollama_base_url,
            model=model,
            timeout=timeout,
            keep_alive=keep_alive,
            media_root=media_root,
        )
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{api_base}/internal/v1/matches", json=payload)
            response.raise_for_status()
            match_id = response.json().get("id")
    except Exception as exc:  # noqa: BLE001
        write_state(media_root, job_id, analysis_status="failed", error=str(exc))
        raise

    write_state(media_root, job_id, analysis_status="completed", match_id=match_id, error=None)
    print(f"analyzed job={job_id} match_id={match_id} model={model}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
