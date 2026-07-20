"use client";

import { FormEvent, useEffect, useState } from "react";
import { createVideoJob, listVideoJobs, type VideoJob } from "@/lib/api";

export default function VideosPage() {
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setJobs(await listVideoJobs());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void load();
  }, []);

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

  return (
    <>
      <h1>Valorant 取り込み</h1>
      <p className="lead">
        大きな動画はここからアップロードしません。Windows の{" "}
        <span className="mono">media/inbox/</span>{" "}
        にファイルを置いてから、ファイル名だけ登録してください。
      </p>
      {error && <p className="bad">{error}</p>}
      <section className="panel">
        <form onSubmit={onSubmit}>
          <label htmlFor="filename">inbox 内のファイル名</label>
          <input id="filename" name="filename" required placeholder="match_001.mp4" />
          <button type="submit" disabled={busy}>
            {busy ? "登録中…" : "ジョブを登録"}
          </button>
        </form>
      </section>
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
                  {job.error ? ` · ${job.error}` : ""}
                </div>
              </div>
            </li>
          ))}
          {jobs.length === 0 && <li className="muted">ジョブはまだありません。</li>}
        </ul>
      </section>
    </>
  );
}
