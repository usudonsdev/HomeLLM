# 現行ハードウェア・ソフトウェア構成管理書 (hardware_software_inventory.md)

> **公開リポ注意**: 実 IP / MAC は書かない。実値は `docs/private/inventory.md`（gitignore）へ。雛形は `docs/inventory.example.md`。

## 1. ハードウェア資産・役割分担

### 1.1. 計算ノード（Windows ゲーミングノート）— **本番**
- **役割（重い処理に集中）**:
  - ホスト Ollama（`qwen3.5:9b`）
  - k3s（API、PostgreSQL、動画解析 Job）
  - GPU を使う推論・解析
- **運用**: 完成後に GitHub から取得して本番稼働。WOL で必要なときだけ起動
- **識別子**: 実値は private inventory（LAN / Tailscale / MAC）

### 1.2. エッジノード（Raspberry Pi）— 常時起動・**本番 Web**
- **役割**:
  - Tailscale ゲートウェイ
  - Windows 向け WOL（`etherwake`）
  - **Web フロントエンドのホスティング**（軽量。DB / LLM / 動画処理は載せない）
- **接続**: 自宅ルーターに常時接続

### 1.3. 開発・デモクライアント（デスクトップ PC）
- **役割**: Cursor での設計・実装、**デモ環境での動作確認**、GitHub への Push
- **クラスタ**: デモ用にローカル k3s / k3d / kind 等（本番ノートの k3s とは別インスタンス）
- **注意**: デモ用データ・Secret は本番と共有しない。公開リポへ実値を載せない

## 2. Windows 側の重要な設定

### 2.1. カバー閉鎖時
- 「カバーを閉じたときの動作」= **何もしない**（クラムシェルでサーバー運用）

### 2.2. Wake-on-LAN
- 有線 NIC で Magic Packet による復帰を有効化（手順の詳細は private メモ可）

## 3. ソフトウェア

### 3.1. Windows ネイティブ
- Tailscale、Ollama（`:11434`）、Docker Desktop / WSL2

### 3.2. Windows 上のクラスタ
- **k3s**（採用ディストリビューション）、kubectl

### 3.3. Raspberry Pi
- Tailscale、`etherwake`、Web 配信（Nginx / Caddy / Node 等は実装時に選定）
