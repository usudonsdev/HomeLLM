# 就活・経験データ管理システム設計書 (system_spec.md)

## 1. システム概要
本システムは、学生時代の経験・感情ログを PostgreSQL に完全ローカルで蓄積し、Ollama を「引き出し」として使う個人用プラットフォームである。ゲーム動画解析（タイトル別 pipeline）も同基盤に載せる。

## 2. 役割分担（重要）

| ノード | 常時 | 載せること | 載せないこと |
|--------|------|------------|--------------|
| **Raspberry Pi** | はい | Web フロント、Tailscale、WOL | DB、Ollama、動画 Job、重い API |
| **Windows ノート** | 必要時（WOL） | k3s（API / Postgres / video Jobs）、ホスト Ollama | 静的 Web の常時配信（Pi に寄せる） |

Windows は **重い処理（LLM・解析・DB）に集中**させる。Web の常時ホスティングは Pi に任せる。

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
  ├── Namespace job-hunting: API (FastAPI) + PostgreSQL 15
  ├── Namespace video-analysis: ゲーム別 Job（後続）
  └── [ホスト] Ollama qwen3.5:9b :11434
```

## 5. 特記事項
- **セキュリティ**: 外部クラウド LLM は使わない。公開 GitHub には個人データ・実インフラ識別子を載せない（`docs/security.md`）。
- **GPU**: Ollama は Windows ネイティブ。k3s Pod からホスト到達可能なアドレスで呼ぶ（実 IP はローカル設定）。
- **動画解析**: ゲーム別 pipeline（`docs/k8s_Architecture.md`、ADR-004）。
