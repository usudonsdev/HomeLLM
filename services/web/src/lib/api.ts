export function jobHuntingApiBase(): string {
  return (process.env.NEXT_PUBLIC_JOB_HUNTING_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

export function videoIngestApiBase(): string {
  return (process.env.NEXT_PUBLIC_VIDEO_INGEST_API_URL || "http://127.0.0.1:8090").replace(/\/$/, "");
}

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export type Experience = {
  id: string;
  category: string;
  title: string;
  org_name: string | null;
  start_date: string;
  end_date: string | null;
  description: string;
  lessons_learned: string | null;
  emotional_log: string | null;
  tags: string[];
};

export type VideoJob = {
  id: string;
  game: string;
  filename: string;
  status: string;
  round_count?: number | null;
  error?: string | null;
  updated_at?: string | null;
};

export async function fetchJobHuntingHealth() {
  return parseJson<{ status: string; service: string; ollama_model: string }>(
    await fetch(`${jobHuntingApiBase()}/health`),
  );
}

export async function fetchVideoHealth() {
  return parseJson<{ status: string; service: string; inbox_exists: boolean }>(
    await fetch(`${videoIngestApiBase()}/health`),
  );
}

export async function listExperiences() {
  return parseJson<Experience[]>(await fetch(`${jobHuntingApiBase()}/experiences`));
}

export async function createExperience(body: Record<string, unknown>) {
  return parseJson<Experience>(
    await fetch(`${jobHuntingApiBase()}/experiences`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function deleteExperience(id: string) {
  const res = await fetch(`${jobHuntingApiBase()}/experiences/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
}

export async function deleteExperiencesByTitle(title: string) {
  const q = new URLSearchParams({ title });
  return parseJson<{ deleted: number; title: string }>(
    await fetch(`${jobHuntingApiBase()}/experiences?${q}`, { method: "DELETE" }),
  );
}

export async function askRag(query: string, keywords: string[]) {
  return parseJson<{
    query: string;
    matched_count: number;
    context_titles: string[];
    answer: string;
    ollama_reachable: boolean;
    model: string;
  }>(
    await fetch(`${jobHuntingApiBase()}/rag/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, keywords }),
    }),
  );
}

export async function listVideoJobs() {
  return parseJson<VideoJob[]>(await fetch(`${videoIngestApiBase()}/v1/jobs`));
}

export async function createVideoJob(filename: string) {
  return parseJson<VideoJob>(
    await fetch(`${videoIngestApiBase()}/v1/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ game: "valorant", filename }),
    }),
  );
}
