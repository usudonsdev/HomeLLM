# データベース構造定義書 (db_spec.md)

## 1. 概要
本システムは PostgreSQL 15 を使用し、構造化データ（カテゴリ、日付、企業名など）と非構造化データ（感情ログ、得たもの、試行錯誤のディテール）を組み合わせて管理する。LLMへコンテキストを渡す際、情報過多で破綻（Lost in the Middle現象）させないよう、キーワードやタグで厳選抽出（RAGの前処理）を行うためのスキーマ設計とする。

## 2. テーブル定義 (DDL)

### 2.1. `experiences` (経験メインテーブル)
あらゆる活動（授業、インターン、個人製作、部活、イベント）の生データを格納する。

```sql
CREATE TABLE experiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(20) NOT NULL, -- 'class', 'intern', 'project', 'club', 'event'
    title VARCHAR(255) NOT NULL, -- 例: 'MIPSアセンブリ課題', '部活Tシャツ販売案内'
    org_name VARCHAR(255),        -- 例: '〇〇大学', '株式会社〇〇', 'パソコン部'
    start_date DATE NOT NULL,
    end_date DATE,                -- NULLの場合は「現在も継続中」
    description TEXT NOT NULL,    -- 概要、客観的事実
    lessons_learned TEXT,         -- 得たもの、学び、成果
    emotional_log TEXT,           -- 感じたこと、泥臭い試行錯誤、葛藤、裏話（LLMの引き出し用）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2. `tags` (タグマスタテーブル)
技術スタックやソフトスキル、キーワードを管理する。

```sql
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL -- 例: 'MIPS', 'Docker', 'チーム開発', 'トラブルシューティング'
);
```

### 2.3. `experience_tags` (中間テーブル)
経験とタグの多対多の結びつきを管理する。

```sql
CREATE TABLE experience_tags (
    experience_id UUID REFERENCES experiences(id) ON DELETE CASCADE,
    tag_id INT REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (experience_id, tag_id)
);
```

## 3. RAG（検索拡張生成）におけるデータ抽出アルゴリズム案
1. フロントエンドから「チーム開発における葛藤について面接用にまとめたい」などのリクエストを受ける。
2. バックエンドは `tags.name` から「チーム開発」を、または `emotional_log` に対する全文検索でキーワードがヒットする `experiences` レコードを抽出。
3. 抽出された最大3〜5件の `lessons_learned` と `emotional_log` の生テキストのみを抽出し、Ollama のプロンプトへコンテキストとして注入する。これにより、クラウドLLMで発生しがちな「情報過多によるコンテキスト無視」を回避し、ローカルLLMでも極めて正確な自己分析の言語化が可能となる。

動画解析（Valorant 等）のスキーマは **`docs/video_db_spec.md`**（`video-analysis` 専用 Postgres）。本書の `experiences` とは分離する。
