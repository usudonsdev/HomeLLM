CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS video_matches (
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

CREATE TABLE IF NOT EXISTS video_rounds (
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

CREATE INDEX IF NOT EXISTS idx_video_rounds_match ON video_rounds(match_id, round_index);
CREATE INDEX IF NOT EXISTS idx_video_rounds_highlight ON video_rounds(match_id) WHERE highlight = TRUE;
