"use client";

import { FormEvent, useState } from "react";
import { askRag } from "@/lib/api";

export default function RagPage() {
  const [answer, setAnswer] = useState<string>("");
  const [meta, setMeta] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const query = String(fd.get("query") || "");
    const keywords = String(fd.get("keywords") || "")
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);
    setBusy(true);
    setError(null);
    try {
      const res = await askRag(query, keywords.length ? keywords : [query]);
      setAnswer(res.answer);
      setMeta(
        `ヒット ${res.matched_count} 件 · Ollama ${res.ollama_reachable ? "接続OK" : "不通"} · モデル ${res.model} · 文脈: ${res.context_titles.join(" / ") || "なし"}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>引き出し（RAG）</h1>
      <p className="lead">
        経験ログを数件だけ拾って、ホスト上の Ollama に聞きます。クラウド LLM
        には送りません。初回は数分かかることがあります。
      </p>
      {error && <p className="bad">{error}</p>}
      <section className="panel">
        <form onSubmit={onSubmit}>
          <label htmlFor="query">聞きたいこと</label>
          <textarea
            id="query"
            name="query"
            required
            placeholder="トラブルシューティングの経験を面接向けにまとめて"
          />
          <label htmlFor="keywords">キーワード / タグ</label>
          <input id="keywords" name="keywords" placeholder="トラブルシューティング" />
          <button type="submit" disabled={busy}>
            {busy ? "考えています…" : "聞く"}
          </button>
        </form>
      </section>
      {(meta || answer) && (
        <section className="panel">
          {meta && <p className="muted mono">{meta}</p>}
          <div className="pre">{answer}</div>
        </section>
      )}
    </>
  );
}
