# 動画解析ドメイン DB 定義書 (video_db_spec.md)

`job-hunting` とは **別 Namespace・別 Postgres**（`video-analysis`）で管理する。就活の `experiences` テーブルとは共有しない。

## 1. テーブル定義

### 1.1. `video_matches`（試合単位の詳細分析）

```sql
CREATE TABLE video_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingest_job_id UUID UNIQUE NOT NULL,
    game VARCHAR(32) NOT NULL DEFAULT 'valorant',
    source_filename VARCHAR(512) NOT NULL,
    title VARCHAR(255) NOT NULL,
    detail_analysis TEXT NOT NULL,
    lessons_learned TEXT,
    emotional_log TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'analyzed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 1.2. `video_rounds`（ラウンド単位メモ + ハイライト）

```sql
CREATE TABLE video_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES video_matches(id) ON DELETE CASCADE,
    round_index INT NOT NULL,
    clip_path TEXT NOT NULL,
    facts TEXT,
    lessons_learned TEXT,
    emotional_log TEXT,
    highlight BOOLEAN NOT NULL DEFAULT FALSE,
    highlight_reason TEXT,
    keyframe_paths JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (match_id, round_index)
);

CREATE INDEX idx_video_rounds_match ON video_rounds(match_id, round_index);
CREATE INDEX idx_video_rounds_highlight ON video_rounds(match_id) WHERE highlight = TRUE;
```

## 2. API 所有者

| エンドポイント | サービス |
|----------------|----------|
| `POST /internal/v1/matches` | `video-ingest-api`（analyzer からの sink） |
| `GET /v1/matches` | `video-ingest-api` |
| `GET /v1/matches/{id}` | `video-ingest-api` |
| `PATCH /v1/rounds/{id}` | `video-ingest-api`（手動ハイライト） |
| `POST /v1/tips` | `video-ingest-api`（傾向 + 上達 Tip、Ollama） |

## 3. Tip 生成

- 最大 3〜5 件のラウンドメモ（`highlight` 優先）の `lessons_learned` + `emotional_log` のみを Ollama に渡す
- 試合詳細全文はデフォルトで渡さない

## 4. job-hunting との関係

- **自動 sink しない**。Valorant 解析データは video-analysis 側に完結する
- 将来、ユーザーが明示的に「就活引き出しへコピー」する機能を別途追加可能（任意の HTTP 連携）
