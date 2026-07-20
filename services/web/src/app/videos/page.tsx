"use client";

import { DragEvent, FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  createVideoJob,
  fetchVideoHealth,
  getVideoMatch,
  listVideoJobs,
  listVideoMatches,
  patchVideoRound,
  uploadVideoJob,
  type VideoJob,
  type VideoMatchDetail,
  type VideoMatchSummary,
} from "@/lib/api";

const DEFAULT_INBOX = String.raw`Documents\HomeLLM\videos\inbox`;
const DEFAULT_MAX = 32 * 1024 * 1024 * 1024;

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export default function VideosPage() {
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [matches, setMatches] = useState<VideoMatchSummary[]>([]);
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<VideoMatchDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [inboxHint, setInboxHint] = useState(DEFAULT_INBOX);
  const [uploadMax, setUploadMax] = useState(DEFAULT_MAX);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      const [jobRows, matchRows] = await Promise.all([listVideoJobs(), listVideoMatches()]);
      setJobs(jobRows);
      setMatches(matchRows);
      const nextId =
        selectedMatchId && matchRows.some((item) => item.id === selectedMatchId)
          ? selectedMatchId
          : (matchRows[0]?.id ?? null);
      setSelectedMatchId(nextId);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void load();
    void (async () => {
      try {
        const health = await fetchVideoHealth();
        if (health.host_inbox_hint) setInboxHint(health.host_inbox_hint);
        if (health.upload_max_bytes) setUploadMax(health.upload_max_bytes);
      } catch {
        /* health is optional for page render */
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedMatchId) {
      setSelectedMatch(null);
      return;
    }
    void (async () => {
      try {
        setSelectedMatch(await getVideoMatch(selectedMatchId));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, [selectedMatchId]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const filename = String(fd.get("filename") || "").trim();
    setBusy(true);
    try {
      await createVideoJob(filename);
      e.currentTarget.reset();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleFile(file: File | null) {
    if (!file) return;
    if (file.size > uploadMax) {
      setError(
        `「${file.name}」は ${formatBytes(file.size)} で上限 ${formatBytes(uploadMax)} を超えています。` +
          ` 上限を上げるか、解析ノードの ${inboxHint} に置いてファイル名登録してください。`,
      );
      return;
    }
    setBusy(true);
    try {
      await uploadVideoJob(file);
      setError(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0] ?? null;
    void handleFile(file);
  }

  async function onToggleHighlight(roundId: string, nextHighlight: boolean) {
    setBusy(true);
    try {
      await patchVideoRound(roundId, {
        highlight: nextHighlight,
        highlight_reason: nextHighlight ? "UI から手動指定" : null,
      });
      if (selectedMatchId) {
        setSelectedMatch(await getVideoMatch(selectedMatchId));
      }
      const matchRows = await listVideoMatches();
      setMatches(matchRows);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const highlightRounds = selectedMatch?.rounds.filter((item) => item.highlight) ?? [];
  const normalRounds = selectedMatch?.rounds.filter((item) => !item.highlight) ?? [];

  return (
    <>
      <h1>Valorant 取り込み</h1>
      <p className="lead">
        いま開いている PC から、下へドラッグ＆ドロップ（またはクリック選択）でアップロードできます。
        ファイルはブラウザから解析用 Windows API へ直接送られます（上限 {formatBytes(uploadMax)}）。
      </p>
      {error && <p className="bad">{error}</p>}
      <section className="panel">
        <div className="toolbar">
          <h2 style={{ margin: 0, flex: 1 }}>分析ビュー</h2>
          <Link href="/videos/tips/" className="secondary">
            傾向と Tip
          </Link>
        </div>
        <p className="muted">`ready` の後に analyzer Job が走り、試合詳細とハイライトが保存されます。</p>
      </section>
      <section className="panel">
        <h2>この PC からアップロード</h2>
        <div
          className={`dropzone${dragOver ? " dropzone-active" : ""}`}
          onDragEnter={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
        >
          <strong>{busy ? "アップロード中…" : "ここに mp4 などをドロップ"}</strong>
          <span className="muted">このクライアント PC のファイルを選択 · 上限 {formatBytes(uploadMax)}</span>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".mp4,.mkv,.webm,.mov,video/*"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0] ?? null;
            e.target.value = "";
            void handleFile(file);
          }}
        />
      </section>
      <details className="panel">
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>上級: 解析ノードに直接置いて登録</summary>
        <p className="muted">
          超巨大ファイル向けの補助手段です。通常は上のアップロードを使ってください。
        </p>
        <form onSubmit={onSubmit}>
          <label htmlFor="filename">解析ノード inbox 内のファイル名</label>
          <input id="filename" name="filename" required placeholder="match_001.mp4" />
          <p className="muted" style={{ marginTop: 0 }}>
            置き場所（解析用 Windows）: <span className="mono">{inboxHint}</span>
          </p>
          <button type="submit" disabled={busy}>
            {busy ? "登録中…" : "ジョブを登録"}
          </button>
        </form>
      </details>
      <section className="panel">
        <div className="toolbar">
          <h2 style={{ margin: 0, flex: 1 }}>ジョブ一覧</h2>
          <button type="button" className="secondary" onClick={() => void load()}>
            再読み込み
          </button>
        </div>
        <ul className="list">
          {jobs.map((job) => (
            <li key={job.id}>
              <div className="list-body">
                <strong>{job.filename}</strong>
                <div className="muted mono">
                  {job.status}
                  {job.round_count != null ? ` · ラウンド ${job.round_count}` : ""}
                  {job.analysis_status ? ` · analysis ${job.analysis_status}` : ""}
                  {job.error ? ` · ${job.error}` : ""}
                </div>
              </div>
            </li>
          ))}
          {jobs.length === 0 && <li className="muted">ジョブはまだありません。</li>}
        </ul>
      </section>
      <section className="panel">
        <div className="toolbar">
          <h2 style={{ margin: 0, flex: 1 }}>試合一覧</h2>
          <button type="button" className="secondary" onClick={() => void load()}>
            再読み込み
          </button>
        </div>
        <ul className="list">
          {matches.map((match) => (
            <li key={match.id}>
              <div className="list-body">
                <strong>{match.title}</strong>
                <div className="muted">
                  {match.source_filename} · ラウンド {match.round_count} · ハイライト {match.highlight_count}
                </div>
              </div>
              <div className="row-actions">
                <button type="button" className="secondary" onClick={() => setSelectedMatchId(match.id)}>
                  詳細
                </button>
              </div>
            </li>
          ))}
          {matches.length === 0 && <li className="muted">まだ分析済みの試合はありません。</li>}
        </ul>
      </section>
      {selectedMatch && (
        <section className="panel">
          <h2>{selectedMatch.title}</h2>
          <p className="muted">
            {selectedMatch.source_filename} · ラウンド {selectedMatch.round_count} · ハイライト{" "}
            {selectedMatch.highlight_count}
          </p>
          <pre style={{ whiteSpace: "pre-wrap", margin: "1rem 0" }}>{selectedMatch.detail_analysis}</pre>
          {selectedMatch.lessons_learned && (
            <>
              <h3>試合全体の学び</h3>
              <p>{selectedMatch.lessons_learned}</p>
            </>
          )}
          {selectedMatch.emotional_log && (
            <>
              <h3>試合全体の感情ログ</h3>
              <p>{selectedMatch.emotional_log}</p>
            </>
          )}
          <h3>注目ラウンド</h3>
          <ul className="list">
            {highlightRounds.map((round) => (
              <li key={round.id}>
                <div className="list-body">
                  <strong>Round {round.round_index}</strong>
                  <div className="muted mono">{round.clip_path}</div>
                  <div>{round.facts}</div>
                  {round.lessons_learned && <div>学び: {round.lessons_learned}</div>}
                  {round.emotional_log && <div>感情: {round.emotional_log}</div>}
                  {round.highlight_reason && <div className="muted">理由: {round.highlight_reason}</div>}
                </div>
                <div className="row-actions">
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy}
                    onClick={() => void onToggleHighlight(round.id, false)}
                  >
                    ハイライト解除
                  </button>
                </div>
              </li>
            ))}
            {highlightRounds.length === 0 && <li className="muted">まだハイライトはありません。</li>}
          </ul>
          <h3>その他のラウンド</h3>
          <ul className="list">
            {normalRounds.map((round) => (
              <li key={round.id}>
                <div className="list-body">
                  <strong>Round {round.round_index}</strong>
                  <div className="muted mono">{round.clip_path}</div>
                  <div>{round.facts}</div>
                  {round.lessons_learned && <div>学び: {round.lessons_learned}</div>}
                </div>
                <div className="row-actions">
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy}
                    onClick={() => void onToggleHighlight(round.id, true)}
                  >
                    ハイライト化
                  </button>
                </div>
              </li>
            ))}
            {normalRounds.length === 0 && <li className="muted">非ハイライトのラウンドはありません。</li>}
          </ul>
        </section>
      )}
    </>
  );
}
