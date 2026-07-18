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
      <h1>Valorant ingest</h1>
      <p className="lead">
        Do not upload multi-GB files through this UI. Copy the video into the Windows{" "}
        <span className="mono">media/inbox/</span> folder first, then register the basename here.
      </p>
      {error && <p className="bad">{error}</p>}
      <section className="panel">
        <form onSubmit={onSubmit}>
          <label htmlFor="filename">Filename in inbox</label>
          <input id="filename" name="filename" required placeholder="match_001.mp4" />
          <button type="submit" disabled={busy}>
            {busy ? "Registering…" : "Register Valorant job"}
          </button>
        </form>
      </section>
      <section className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
          <h2>Jobs</h2>
          <button type="button" className="secondary" onClick={() => void load()}>
            Refresh
          </button>
        </div>
        <ul className="list">
          {jobs.map((job) => (
            <li key={job.id}>
              <strong>{job.filename}</strong>
              <div className="muted mono">
                {job.status}
                {job.round_count != null ? ` · rounds=${job.round_count}` : ""}
                {job.error ? ` · ${job.error}` : ""}
              </div>
            </li>
          ))}
          {jobs.length === 0 && <li className="muted">No video jobs yet.</li>}
        </ul>
      </section>
    </>
  );
}
