"use client";

import { useEffect, useState } from "react";
import { fetchVideoTips, listVideoMatches, type VideoMatchSummary, type VideoTipsResponse } from "@/lib/api";

export default function VideoTipsPage() {
  const [matches, setMatches] = useState<VideoMatchSummary[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [tips, setTips] = useState<VideoTipsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const rows = await listVideoMatches();
        setMatches(rows);
        setSelected(rows.slice(0, 3).map((item) => item.id));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, []);

  async function onGenerate() {
    setBusy(true);
    try {
      setTips(await fetchVideoTips(selected));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function onToggle(id: string) {
    setSelected((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  }

  return (
    <>
      <h1>Valorant の傾向と Tip</h1>
      <p className="lead">ハイライト優先のラウンドメモから、最近の傾向と次に試す改善案を Ollama で要約します。</p>
      {error && <p className="bad">{error}</p>}
      <section className="panel">
        <h2>対象試合</h2>
        <ul className="list">
          {matches.map((match) => (
            <li key={match.id}>
              <label style={{ display: "flex", gap: "0.75rem", alignItems: "center", width: "100%" }}>
                <input
                  type="checkbox"
                  checked={selected.includes(match.id)}
                  onChange={() => onToggle(match.id)}
                />
                <span>
                  <strong>{match.title}</strong>
                  <span className="muted">{" "}· {match.source_filename} · ハイライト {match.highlight_count}</span>
                </span>
              </label>
            </li>
          ))}
          {matches.length === 0 && <li className="muted">分析済み試合がまだありません。</li>}
        </ul>
        <button type="button" disabled={busy || matches.length === 0} onClick={() => void onGenerate()}>
          {busy ? "生成中…" : "Tip を生成"}
        </button>
      </section>
      {tips && (
        <section className="panel">
          <h2>生成結果</h2>
          <p className="muted">
            参照ラウンド {tips.matched_count} · モデル {tips.model}
            {!tips.ollama_reachable ? " · Ollama 未接続" : ""}
          </p>
          <pre style={{ whiteSpace: "pre-wrap" }}>{tips.answer}</pre>
        </section>
      )}
    </>
  );
}
