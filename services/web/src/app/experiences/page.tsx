"use client";

import { FormEvent, useEffect, useState } from "react";
import { createExperience, listExperiences, type Experience } from "@/lib/api";

export default function ExperiencesPage() {
  const [items, setItems] = useState<Experience[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setItems(await listExperiences());
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
    const tags = String(fd.get("tags") || "")
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    setBusy(true);
    try {
      await createExperience({
        category: fd.get("category"),
        title: fd.get("title"),
        org_name: fd.get("org_name") || null,
        start_date: fd.get("start_date"),
        description: fd.get("description"),
        lessons_learned: fd.get("lessons_learned") || null,
        emotional_log: fd.get("emotional_log") || null,
        tags,
      });
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
      <h1>Experiences</h1>
      <p className="lead">Structured logs for the local RAG drawer. Keep personal detail off GitHub.</p>
      {error && <p className="bad">{error}</p>}
      <section className="panel">
        <form onSubmit={onSubmit}>
          <label htmlFor="category">Category</label>
          <select id="category" name="category" required defaultValue="project">
            <option value="class">class</option>
            <option value="intern">intern</option>
            <option value="project">project</option>
            <option value="club">club</option>
            <option value="event">event</option>
          </select>
          <label htmlFor="title">Title</label>
          <input id="title" name="title" required />
          <label htmlFor="org_name">Org</label>
          <input id="org_name" name="org_name" />
          <label htmlFor="start_date">Start date</label>
          <input id="start_date" name="start_date" type="date" required />
          <label htmlFor="description">Description</label>
          <textarea id="description" name="description" required />
          <label htmlFor="lessons_learned">Lessons learned</label>
          <textarea id="lessons_learned" name="lessons_learned" />
          <label htmlFor="emotional_log">Emotional log</label>
          <textarea id="emotional_log" name="emotional_log" />
          <label htmlFor="tags">Tags (comma separated)</label>
          <input id="tags" name="tags" placeholder="Docker, チーム開発" />
          <button type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save experience"}
          </button>
        </form>
      </section>
      <section className="panel">
        <h2>Stored ({items.length})</h2>
        <ul className="list">
          {items.map((item) => (
            <li key={item.id}>
              <strong>{item.title}</strong>
              <div className="muted">
                {item.category} · {item.start_date}
                {item.tags.length ? ` · ${item.tags.join(", ")}` : ""}
              </div>
            </li>
          ))}
          {items.length === 0 && <li className="muted">No experiences yet.</li>}
        </ul>
      </section>
    </>
  );
}
