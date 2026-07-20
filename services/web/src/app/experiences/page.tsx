"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  createExperience,
  deleteExperience,
  deleteExperiencesByTitle,
  listExperiences,
  type Experience,
} from "@/lib/api";

const SMOKE_TITLE = "HomeLLM smoke experience";

const categoryLabels: Record<string, string> = {
  class: "授業",
  intern: "インターン",
  project: "個人・チーム開発",
  club: "部活・サークル",
  event: "イベント",
};

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

  async function onDeleteOne(id: string) {
    if (!window.confirm("この経験ログを削除しますか？")) return;
    setBusy(true);
    try {
      await deleteExperience(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onClearSmoke() {
    if (!window.confirm(`タイトル「${SMOKE_TITLE}」のテストデータをすべて削除しますか？`)) return;
    setBusy(true);
    try {
      const res = await deleteExperiencesByTitle(SMOKE_TITLE);
      setError(null);
      await load();
      window.alert(`${res.deleted} 件削除しました`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>経験ログ</h1>
      <p className="lead">
        ローカル RAG 用の構造化メモです。個人の生データは GitHub に載せないでください。
      </p>
      {error && <p className="bad">{error}</p>}
      <section className="panel">
        <form onSubmit={onSubmit}>
          <label htmlFor="category">カテゴリ</label>
          <select id="category" name="category" required defaultValue="project">
            <option value="class">授業</option>
            <option value="intern">インターン</option>
            <option value="project">個人・チーム開発</option>
            <option value="club">部活・サークル</option>
            <option value="event">イベント</option>
          </select>
          <label htmlFor="title">タイトル</label>
          <input id="title" name="title" required />
          <label htmlFor="org_name">組織・団体</label>
          <input id="org_name" name="org_name" />
          <label htmlFor="start_date">開始日</label>
          <input id="start_date" name="start_date" type="date" required />
          <label htmlFor="description">内容</label>
          <textarea id="description" name="description" required />
          <label htmlFor="lessons_learned">学び</label>
          <textarea id="lessons_learned" name="lessons_learned" />
          <label htmlFor="emotional_log">感情ログ</label>
          <textarea id="emotional_log" name="emotional_log" />
          <label htmlFor="tags">タグ（カンマ区切り）</label>
          <input id="tags" name="tags" placeholder="Docker, チーム開発" />
          <button type="submit" disabled={busy}>
            {busy ? "保存中…" : "保存する"}
          </button>
        </form>
      </section>
      <section className="panel">
        <div className="toolbar">
          <h2 style={{ margin: 0, flex: 1 }}>保存済み（{items.length}）</h2>
          <button type="button" className="danger" disabled={busy} onClick={() => void onClearSmoke()}>
            テストデータを削除
          </button>
        </div>
        <ul className="list">
          {items.map((item) => (
            <li key={item.id}>
              <div className="list-body">
                <strong>{item.title}</strong>
                <div className="muted">
                  {categoryLabels[item.category] || item.category} · {item.start_date}
                  {item.tags.length ? ` · ${item.tags.join(", ")}` : ""}
                </div>
              </div>
              <div className="row-actions">
                <button
                  type="button"
                  className="danger"
                  disabled={busy}
                  onClick={() => void onDeleteOne(item.id)}
                >
                  削除
                </button>
              </div>
            </li>
          ))}
          {items.length === 0 && <li className="muted">まだ経験ログはありません。</li>}
        </ul>
      </section>
    </>
  );
}
