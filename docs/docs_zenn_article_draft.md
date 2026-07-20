# Zenn記事下書き: HomeLLM をデスクトップからノート＋Piへ移植して苦戦した話

---
title: "完全ローカル就活AIを「動くところ」まで運ぶ：k3d・Ollama・Raspberry Pi・Tailscaleでハマった全部"
emoji: "🛠️"
type: "tech"
topics: ["ollama", "kubernetes", "raspberrypi", "tailscale", "fastapi", "nextjs", "cursor"]
published: false
---

## はじめに

就活の経験ログや感情ログは、クラウド LLM に生で投げたくない個人情報の塊です。  
そこで **ゲーミングノート（重い計算）＋ Raspberry Pi（薄い Web 常時配信）＋ デスクトップ（開発）** で、完全ローカルの「引き出し」を作りました。

この記事は成功談というより、**「設計は合っているのに、画面が DOWN のまま数日溶かした」移植記**です。  
Gemini に相談しつつ回り道し、最終的には Cursor と実ログで一本化した話も含みます。

公開リポジトリ運用なので、本文の IP / ホスト名はすべてプレースホルダにしています。

## 最終形（役割分担だけ先に）

```text
[ブラウザ] --Tailscale--> [Raspberry Pi: 静的 Web]
                              |
                              | fetch (NEXT_PUBLIC_* に焼いた URL)
                              v
                    [Windows ノート: API / Postgres / Jobs]
                              |
                              v
                    [同一ホストの Ollama :11434]  ← Pod には入れない
```

| マシン | やること | やらないこと |
|--------|----------|--------------|
| デスクトップ | 実装・デモ（k3d）・GitHub Push | 本番個人データの常駐 |
| ゲーミングノート | 本番相当の API / DB / 動画 Job / ホスト Ollama | Web の常時配信 |
| Raspberry Pi | 静的フロント・Tailscale・（将来）WOL | DB / LLM / 重い Job |

開発フローは **デスクトップで動かす → push → ノートで pull** です。Compose を本番にしない、Ollama は Windows ネイティブ、という方針は最初から固定しました。

## なぜ苦戦したのか（結論の先出し）

障害はだいたい次の層に分かれます。**一度に全部疑うと終わりません。**

1. **どのマシンの話か**が混ざる（パス / IP / port-forward）
2. **ブラウザが叩く先**と **いま生きている API** がズレる（Next の `NEXT_PUBLIC_*` はビルド時焼き込み）
3. **Pod → ホスト Ollama** の DNS（`host.k3d.internal` が解けない）
4. **Windows + PowerShell** の引用符・ExecutionPolicy
5. **ローカル LLM が遅い**（ping で 40 秒、thinking モデル）
6. **ブラウザの Private Network Access (PNA)** が `Failed to fetch` に見える

以下、時系列で拾います。

---

## 第1幕: ノートに API を載せたが、Ollama に届かない

ノートで k3d（k3s-in-Docker）に `job-hunting-api` と Postgres を載せました。  
`kubectl get pods` には Ollama の Pod がありません。**これはバグではなく設計です。**

API の ConfigMap は当初こうでした。

```text
OLLAMA_BASE_URL=http://ollama.job-hunting.svc.cluster.local:11434
```

これはクラスター内の **ExternalName Service** で、実体はホスト側 Ollama への橋です。  
ところが `/health/ollama` がこう返しました。

```json
{
  "ok": false,
  "error": "[Errno -2] Name or service not known",
  "models": []
}
```

外部 AI は「Ollama Pod が無いから 502」「Service の IP がズレている」と推測しがちですが、決定打は **名前解決失敗** です。  
k3d 公式が勧める `host.k3d.internal` が、Docker Desktop 上の Pod 内で解けないケースがありました。

**直し方（デモ環境）:** 到達先を `host.docker.internal` に寄せる。

```yaml
# イメージ（実ファイルはリポの k8s/job-hunting/ を参照）
OLLAMA_BASE_URL: "http://host.docker.internal:11434"
# ExternalName も同様に host.docker.internal
```

適用後:

```powershell
curl.exe -s http://127.0.0.1:8000/health/ollama
# "ok": true と models 一覧が出れば Pod→ホスト経路は生きている
```

補足: ホストの Ollama は `127.0.0.1` だけ待受だとコンテナから届きません。必要なら `OLLAMA_HOST=0.0.0.0` にして **トレイから Quit → 再起動**。

---

## 第2幕: PowerShell がすべてを難しくする

移植中、次が何度も出ました。

### `kubectl patch` の JSON が壊れる

```text
error decoding patch: invalid character 'd' looking for beginning of object key string
```

Bash 感覚の単一引用符 JSON を Windows PowerShell にそのまま貼ると、**ネイティブ引数に渡る前に `"` が剥がれる**ことがあります。  
モデル名を変えたいだけなら JSON を避けます。

```powershell
kubectl -n job-hunting set env deployment/job-hunting-api OLLAMA_MODEL=qwen3.5:9b
```

どうしても patch するなら:

```powershell
kubectl -n job-hunting patch configmap api-config --type merge -p "{\"data\":{\"OLLAMA_MODEL\":\"qwen3.5:9b\"}}"
```

### ExecutionPolicy

```text
このシステムではスクリプトの実行が無効になっているため ... smoke_test.ps1 を読み込むことができません
```

恒久なら管理者 PowerShell で:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

一時しのぎなら:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
```

### パス地獄

ノートの実体は `...\OneDrive\Desktop\Myproject\HomeLLM`、指示文は `Documents\GitHub\HomeLLM`、カレントは `services\web` のまま `cd ..` 一回で `scripts` を探す——全部やりました。  
**コマンドの前に `pwd` と「どの PC か」を書く**のが一番安い保険です。

---

## 第3幕: RAG が `Ollama generate failed: `（中身が空）

`/health` と `/experiences` は通るのに `/rag/ask` だけ落ちる。  
ホスト直叩きの ping は成功するが **総時間 ≈ 40 秒**（ロード十数秒＋生成）。

ここで「モデルを 7B に落とせ」「FastAPI のデフォルト 30 秒」と誘導されがちですが、この構成では:

- Ollama は **ホスト**（k8s Deployment のログを漁っても無い）
- API の httpx はもともと長めのタイムアウトを持っていたが、**ノートの実測には足りない／コールドロードが痛い**

実効的だったのは次です。

1. **モデルは品質優先で `qwen3.5:9b` のまま**
2. generate に `keep_alive`（例: `24h`）を付けて常駐
3. タイムアウトを 300 秒前後まで延ばす
4. 例外メッセージを空にしない（status / body を 502 に載せる）
5. smoke の `curl` にも `--max-time` を付ける

ウォームアップ例:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" `
  -Method Post -ContentType "application/json" `
  -Body '{"model":"qwen3.5:9b","prompt":"ping","stream":false,"keep_alive":"24h"}'
```

thinking 系は「固まったように見える」のが普通です。空レスポンスとタイムアウトは別物として切り分けます。

---

## 第4幕: Pi の Status は UP なのに API だけ DOWN

Pi に静的エクスポートを載せると UI は出ます。感動の直後に Status が赤。

### 罠1: 焼き込み IP が古い

Next.js の `NEXT_PUBLIC_*` は **ビルド時定数**です。  
デスクトップ結合デモ用に焼いた Tailscale IP のまま Pi に載せると、ノートで API を立てても永遠に `Failed to fetch` です。

```text
# 悪い例のイメージ
ブラウザ(Pi UI) → デスクトップの古い IP:8000  （誰も聞いていない）
# 正しい例のイメージ
ブラウザ(Pi UI) → ノートの現行 Tailscale IP:8000
```

**直し方:** ノート（またはビルドする PC）で `.env.local` を直して **再ビルド → Pi 再デプロイ**。  
port-forward を `0.0.0.0` にするだけでは、**古い IP を叩いている限り直りません**。

### 罠2: port-forward のバインドとファイアウォール

```powershell
kubectl -n job-hunting port-forward --address 0.0.0.0 svc/job-hunting-api 8000:8000
```

- `127.0.0.1` だけだと Tailscale 経由の他ノードから届かない
- 既に別プロセスが 8000 を掴んでいると `bind: Only one usage...`
- Windows ファイアウォールで 8000/8090 を塞いでいると外側から死ぬ

ロールアウト後は **port-forward を必ず繋ぎ直す**（古い Pod 向けトンネルが幽霊化する）。

### 罠3: ブラウザの Private Network Access

開発者ツールにこう出ることがあります。

```text
Access to fetch at 'http://<NOTEBOOK_TS_IP>:8000/health'
from origin 'http://<PI_HOST>/'
has been blocked by CORS policy:
The request client is not a secure context and the resource
is in more-private address space 'local'.
```

見た目は CORS、中身は **非セキュアオリジン（http の .local）から private IP への制限**です。  
検証中の回避例として、Chromium 系の「Insecure origins treated as secure」に Pi の origin を入れる、などがあります（本番では HTTPS 化や同一オリジン設計を検討）。

API 側の `Access-Control-Allow-Origin` だけでは足りない、というのが学びでした。

### デプロイスクリプト側の地雷（Windows）

- `scp out\*` はディレクトリ構造を潰す
- `tar | ssh` のパイプは Windows で壊れやすい → **tar.gz を一度ファイルにして scp**
- `services/web/out` が Explorer / OneDrive で EBUSY → TEMP に退避ビルド

これらを `scripts/deploy-web-pi.ps1` に寄せたあと、ようやく再現可能なデプロイになりました。

---

## 「どの PC で何をするか」チェックリスト

移植で一番高いのは技術より **場所の取り違え** でした。

| 作業 | PC |
|------|-----|
| コード変更・デモ・`git push` | デスクトップ（主） |
| `git pull`・k3d・Ollama・port-forward・smoke | ノート |
| `.env.local` をノート IP にして `deploy-web-pi.ps1` | ビルドできる Windows（ノート推奨） |
| nginx で静的配信 | Pi |
| Status 確認ブラウザ | Tailscale online ならどれでも |

「ノートの API を見たいのにデスクトップの IP が焼いてある」「Documents パスで pull しようとして実体は OneDrive」——この手のミスがログの大半を占めます。

---

## 外部 AI に頼るときの使い方（反省）

便利でしたが、次は外れやすかったです。

- Ollama Pod のログを見ろ（存在しない）
- モデルを闇雲に落とせ（品質要件と無関係）
- port-forward を広げれば焼き込み IP も直る（直らない）
- 全部 CORS（PNA や DNS の別件）

効いた聞き方はこれでした。

> `/health/ollama` の生 JSON と、ブラウザ Network の赤文字をそのまま貼る。  
> 「どの PC・どのカレントディレクトリか」を先に書く。

実ログを読めるエージェント（今回は Cursor）と、設計ドキュメント（ADR / AGENTS.md）を正本にした方が収束が早い、というのが率直な感想です。

---

## いま見える「動く Vertical Slice」

ノート移植後、少なくとも次までは確認できました。

- Pi 上の Production UI が表示される
- Status がノート Tailscale 上の job-hunting API を **UP** と表示する（PNA 回避後）
- Experiences の POST/GET が通る
- Ollama 疎通（`/health/ollama`）は `ok: true`
- RAG は重いので、体感確認は後回しでもプロダクトとしては「触れる」

動画 ingest（8090）や本番 k3s（k3d ではない）は次フェーズです。

---

## おわりに

「完全ローカル」はロマンですが、実作業の大半は LLM より **DNS・ファイアウォール・ビルド時環境変数・どのマシンか** です。  
それでも、個人情報を外に出さずに ES 用の引き出しを自宅 LAN / Tailscale 内に置ける価値は大きいと感じています。

同じ構成を試す人への最短ルート:

1. デスクトップで縦スライスを一度完成させて push  
2. ノートで pull → Ollama はホスト、API は `host.docker.internal`  
3. Pi には静的だけ載せ、`NEXT_PUBLIC_*` は **ノートの現行 IP で焼き直す**  
4. Status が赤なら、先に DevTools の Network を見る（CORS に騙されない）

リポジトリと設計メモは公開前提で整理しています。秘密情報・実 IP・経験の生データは gitignore / private 側へ。

（下書き。公開前にスクリーンショット・図・実測秒数を足す想定）
