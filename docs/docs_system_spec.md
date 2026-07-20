# 就活・経験データ管理システム設計書 (system_spec.md)

## 1. システム概要
本システムは、学生時代の経験・感情ログを PostgreSQL に完全ローカルで蓄積し、Ollama を「引き出し」として使う個人用プラットフォームである。ゲーム動画解析（タイトル別 pipeline）は **別サービス**（`video-analysis`）として同居させ、DB は共有しない（ADR-010）。

## 2. 役割分担（重要）

| ノード | 常時 | 載せること | 載せないこと |
|--------|------|------------|--------------|
| **Raspberry Pi** | はい | Web フロント、Tailscale、WOL | DB、Ollama、動画 Job、重い API |
| **Windows ノート** | 必要時（WOL） | k3s（API / Postgres / video Jobs）、ホスト Ollama | 静的 Web の常時配信（Pi に寄せる） |

Windows は **重い処理（LLM・解析・DB）に集中**させる。Web の常時ホスティングは Pi に任せる。

## 2.1. 開発・デモ → 本番の流れ（ADR-007）

1. **デスクトップ**: 実装とデモ（ローカル k3s 系）。動作確認後 GitHub へ Push
2. **ゲーミングノート（本番）**: `git pull`（または clone）し、private な Secret / IP 設定を入れたうえで k3s + Ollama を起動
3. **Raspberry Pi（本番 Web）**: フロントを配置し、Tailscale 経由でノート上の API を呼ぶ

デモ用 DB・ログに本番の個人データを入れない。

## 3. ネットワーク
- クライアント ↔ 各ノードは **Tailscale 等の私有網**を基本（インターネットへ API/Ollama を直接公開しない）
- 実 IP はリポジトリに書かない（`docs/security.md` / `docs/inventory.example.md`）

## 4. アプリケーションアーキテクチャ

```
[ ブラウザ ]
    │ Tailscale
    ▼
[ Raspberry Pi ]  … Web (Next.js 等) 常時
    │ API 呼び出し (Tailscale)
    ▼
[ Windows + k3s ] … 必要時起動
  ├── Namespace job-hunting: API (FastAPI) + PostgreSQL 15（就活のみ）
  ├── Namespace video-analysis: ingest API + Postgres + Valorant Jobs
  └── [ホスト] Ollama qwen3.5:9b :11434
```

フロント（`services/web`）は **静的エクスポート**し、デスクトップから SSH で Pi に配置する（`scripts/deploy-web-pi.ps1`）。ブラウザは Tailscale 経由で **job-hunting-api** と **video-ingest-api** を別々に呼ぶ（動画バイナリは UI 経由で送らない）。

## 5. 特記事項
- **セキュリティ**: 外部クラウド LLM は使わない。公開 GitHub には個人データ・実インフラ識別子を載せない（`docs/security.md`）。
- **GPU**: Ollama は Windows ネイティブ。k3s Pod からホスト到達可能なアドレスで呼ぶ（実 IP はローカル設定）。
- **動画解析**: ゲーム別 pipeline（`docs/k8s_Architecture.md`、ADR-004）。成果物はクリップだけでなく、**傾向要約と上達 Tip**（ローカル Ollama、厳選コンテキスト）まで含む。スキーマは `docs/video_db_spec.md`。

---

## 6. 動画解析 UX（video-analysis ドメイン）

就活の「引き出し」とは独立。詳細は ADR-009 / ADR-010。

| 段階 | ユーザーが得ること |
|------|-------------------|
| 解析完了 | **試合の詳細分析**と、ラウンドメモが video-analysis DB に残る |
| ハイライト | その試合で **注目すべきラウンド**だけ先に見返せる |
| 横断閲覧 | 試合一覧・期間で自分の傾向を一覧できる |
| Tip | 「最近の傾向に対する上達のヒント」を Ollama が日本語で返す（video-ingest-api） |

実装詳細とパイプライン境界は `docs/k8s_Architecture.md` §2.1、DB は `docs/video_db_spec.md`。
