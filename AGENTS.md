# HomeLLM — Agent Instructions

このリポジトリは **GitHub 公開**前提の、完全ローカル就活データ＋動画解析基盤である。  
**設計の正本は `docs/`。実装前に該当ドキュメントを読むこと。**

## ドキュメント索引

| 文書 | 内容 |
|------|------|
| `docs/security.md` | **公開リポのセキュリティ方針（必読）** |
| `docs/docs_system_spec.md` | 役割分担・全体構成 |
| `docs/docs_db_spec.md` | PostgreSQL・RAG |
| `docs/Architecture_decision.md` | ADR（k3s、Ollama、Pi Web、秘密情報） |
| `docs/k8s_Architecture.md` | Namespace・ゲーム別 pipeline |
| `docs/infra_inventory.md` | ハード役割（実 IP なし） |
| `docs/inventory.example.md` | 実値記入用テンプレ → `docs/private/` |

## ノード役割（破らないこと）

| ノード | 担当 | 禁止 |
|--------|------|------|
| **デスクトップ** | 開発・デモ（ローカル k3s 系）、GitHub Push | 本番個人データ、実インフラ秘密のコミット |
| **Raspberry Pi** | 本番 Web 常時配信、Tailscale、WOL | DB / Ollama / 動画 Job / 重い API |
| **Windows ノート** | **本番** k3s（API・Postgres・video Jobs）、ホスト Ollama | Web の常時ホスティング |

フロー: **デスクトップでデモ → GitHub → ノートで pull して本番**（ADR-007）。Windows は重い処理に集中（ADR-005）。

## 公開リポ・セキュリティ（最優先）
詳細は `docs/security.md`。要約:

1. 実 LAN/Tailscale IP、MAC、パスワード、kubeconfig、経験ログ生データをコミットしない
2. Secret は `*.example.yaml` のみ。実値は gitignored
3. クラウド LLM API 禁止。Ollama をインターネットへ無認証公開しない
4. API は Tailscale 内＋認証前提（スモーク段階でも本番デプロイ前に必須化）

## プロダクト原則

1. 完全ローカル AI（既定モデル `qwen3.5:9b`）
2. Ollama は Windows ネイティブのみ（コンテナ化しない）
3. RAG は最大 3〜5 件、`lessons_learned` + `emotional_log` のみ注入
4. 本番オーケストレータは **Windows 上の k3s**（Swarm 不採用）。Compose は局所煙テストのみ可
5. 動画はゲーム別 pipeline（Valorant ロゴ分割 → Job、TFT は時間セグメント）

## 目標アーキテクチャ

```
[ ブラウザ ] --Tailscale--> [ Raspberry Pi: Web ]
                                │
                                ▼ API
                         [ Windows + k3s ]  (WOL で必要時)
                           ├── job-hunting: API + Postgres
                           ├── video-analysis: ゲーム別 Job
                           └── host Ollama :11434
```

### 実装フェーズ

1. **デスクトップでデモ**: API + Postgres（ローカル k3s または暫定スモーク）。必要なら簡易 Web
2. **ノートへ本番移植**: GitHub から取得、k3s + Ollama + private 設定
3. **Pi に本番 Web** を載せる
4. Valorant pipeline → TFT 等

## エージェント作業ルール

- 秘密・実インフラ識別子を追加しない。docs に書くならプレースホルダ
- 仕様変更は docs / ADR を先に更新
- 動画ワーカーを巨大モノリスに溶かさない
- ユーザー未依頼の有料クラウド導入・force push はしない

## やってはいけないこと

- 公開リポへ実 IP / 平文パスワード / 個人の経験生データを入れる
- Ollama・Postgres を WAN に晒す
- Web を再び Windows 常時配信に戻して Pi の役割を空にする
- クラウド LLM へ個人ログ送信
