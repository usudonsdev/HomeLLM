"use client";

import { useEffect, useState } from "react";
import {
  fetchJobHuntingHealth,
  fetchVideoHealth,
  jobHuntingApiBase,
  videoIngestApiBase,
} from "@/lib/api";

type Probe = { ok: boolean; detail: string };

export default function StatusPage() {
  const [jobApi, setJobApi] = useState<Probe>({ ok: false, detail: "checking…" });
  const [videoApi, setVideoApi] = useState<Probe>({ ok: false, detail: "checking…" });

  async function refresh() {
    try {
      const h = await fetchJobHuntingHealth();
      setJobApi({ ok: true, detail: `${h.service} / model ${h.ollama_model}` });
    } catch (e) {
      setJobApi({ ok: false, detail: e instanceof Error ? e.message : String(e) });
    }
    try {
      const h = await fetchVideoHealth();
      setVideoApi({
        ok: true,
        detail: `${h.service} / inbox=${h.inbox_exists ? "ready" : "missing"}`,
      });
    } catch (e) {
      setVideoApi({ ok: false, detail: e instanceof Error ? e.message : String(e) });
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <>
      <h1>Status</h1>
      <p className="lead">
        Production UI on the Pi. This page probes Windows APIs over Tailscale (or local
        port-forward for desktop demos).
      </p>
      <div className="grid two">
        <section className="panel">
          <h2>job-hunting API</h2>
          <p className="mono muted">{jobHuntingApiBase()}</p>
          <p className={jobApi.ok ? "ok" : "bad"}>{jobApi.ok ? "UP" : "DOWN"}</p>
          <p className="muted">{jobApi.detail}</p>
        </section>
        <section className="panel">
          <h2>video-ingest API</h2>
          <p className="mono muted">{videoIngestApiBase()}</p>
          <p className={videoApi.ok ? "ok" : "bad"}>{videoApi.ok ? "UP" : "DOWN"}</p>
          <p className="muted">{videoApi.detail}</p>
        </section>
      </div>
      <button type="button" className="secondary" onClick={() => void refresh()}>
        Refresh
      </button>
    </>
  );
}
