# 公開リポジトリ向けセキュリティ方針

本リポジトリは **GitHub 公開**を前提とする。個人情報・自宅インフラの詳細はコード／docs に載せない。

## 絶対にコミットしないもの

- 実 IP（LAN / Tailscale）、MAC アドレス、ホスト名の実体
- DB パスワード、API キー、`.env` の実値
- 就活・経験ログの生データ（氏名、大学名、企業名、感情ログの実文）
- kubeconfig、Tailscale auth key、SSH 秘密鍵
- 本番用 `Secret` マニフェストの実値

## 公開してよいもの

- アーキテクチャ説明（役割分担、Namespace、Job の考え方）
- プレースホルダ付きの設定例（`<WINDOWS_TAILSCALE_IP>` 等）
- ダミー／合成のスモークテスト用 JSON
- Dockerfile、アプリ骨格、`*.example` / `*.example.yaml`

## ネットワーク公開の原則

1. **インターネットへ直接晒さない**: Web / API / Ollama / Postgres は Tailscale（または同等の私有網）内を基本とする。
2. **Ollama は Windows ホストのみ**: コンテナ化しない。LAN/WAN へ無認証公開しない。
3. **API は認証前提**: 公開リポでも、デプロイ先ではアプリ認証または Tailscale 制限を必須とする（現状スモークは未実装 → 実装前に必須化）。
4. **Raspberry Pi の Web**: 静的／フロント配信に限定し、DB・LLM・動画処理を載せない。

## ローカル秘密の置き場

| 用途 | 置き場 |
|------|--------|
| 実 IP・MAC・ホスト固有値 | `docs/private/`（gitignored）またはパスワードマネージャ |
| k8s Secret 実値 | クラスタへ直接 apply / sealed-secrets 等。リポには `*.example.yaml` のみ |
| 環境変数 | `.env`（gitignored）。雛形は `.env.example` |

## 既に漏れた可能性がある場合

履歴に実 IP 等が残っている場合:

1. 可能ならリポジトリを **Private** に戻す、または履歴から除去（`git filter-repo` 等）を検討する
2. Tailscale ACL でノード公開範囲を再確認する
3. DB 等に仮パスワードを使っていた場合は **本番前に必ずローテーション**する
