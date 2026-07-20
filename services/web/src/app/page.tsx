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
  const [jobApi, setJobApi] = useState<Probe>({ ok: false, detail: "確認中…" });
  const [videoApi, setVideoApi] = useState<Probe>({ ok: false, detail: "確認中…" });

  async function refresh() {
    try {
      const h = await fetchJobHuntingHealth();
      setJobApi({ ok: true, detail: `${h.service} / モデル ${h.ollama_model}` });
    } catch (e) {
      setJobApi({ ok: false, detail: e instanceof Error ? e.message : String(e) });
    }
    try {
      const h = await fetchVideoHealth();
      setVideoApi({
        ok: true,
        detail: `${h.service} / inbox=${h.inbox_exists ? "あり" : "なし"}`,
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
      <h1>接続状態</h1>
      <p className="lead">
        Pi 上の画面から、Windows（Tailscale またはデモ用 port-forward）の API
        へ到達できるかを確認します。
      </p>
      <div className="grid two">
        <section className="panel">
          <h2>就活 API</h2>
          <p className="mono muted">{jobHuntingApiBase()}</p>
          <p className={`status-mark ${jobApi.ok ? "ok" : "bad"}`}>
            {jobApi.ok ? "稼働中" : "停止中"}
          </p>
          <p className="muted">{jobApi.detail}</p>
        </section>
        <section className="panel">
          <h2>動画取り込み API</h2>
          <p className="mono muted">{videoIngestApiBase()}</p>
          <p className={`status-mark ${videoApi.ok ? "ok" : "bad"}`}>
            {videoApi.ok ? "稼働中" : "停止中"}
          </p>
          <p className="muted">{videoApi.detail}</p>
        </section>
      </div>
      <button type="button" className="secondary" onClick={() => void refresh()}>
        再確認
      </button>
    </>
  );
}
