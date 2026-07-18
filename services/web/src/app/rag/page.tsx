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
        `matched=${res.matched_count} · ollama=${res.ollama_reachable ? "up" : "down"} · model=${res.model} · contexts=${res.context_titles.join(" | ") || "(none)"}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>RAG drawer</h1>
      <p className="lead">
        Filters a few experience logs, then asks the host Ollama model. Cloud LLM APIs are not used.
      </p>
      {error && <p className="bad">{error}</p>}
      <section className="panel">
        <form onSubmit={onSubmit}>
          <label htmlFor="query">Prompt</label>
          <textarea id="query" name="query" required placeholder="トラブルシューティングの経験を面接向けにまとめて" />
          <label htmlFor="keywords">Keywords / tags</label>
          <input id="keywords" name="keywords" placeholder="トラブルシューティング" />
          <button type="submit" disabled={busy}>
            {busy ? "Asking…" : "Ask"}
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
