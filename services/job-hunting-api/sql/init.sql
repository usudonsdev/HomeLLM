CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS experiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    org_name VARCHAR(255),
    start_date DATE NOT NULL,
    end_date DATE,
    description TEXT NOT NULL,
    lessons_learned TEXT,
    emotional_log TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS experience_tags (
    experience_id UUID REFERENCES experiences(id) ON DELETE CASCADE,
    tag_id INT REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (experience_id, tag_id)
);

INSERT INTO tags (name)
VALUES ('チーム開発'), ('トラブルシューティング'), ('Docker')
ON CONFLICT (name) DO NOTHING;
