# マイクロサービス追加仕様書 (microservice_extensions.md)

## 1. コンポーネントの分離（サービス境界）
本システムは、互いに独立してデプロイ・スケール可能な以下のマイクロサービス群に分割する。

### 1.1. `job-hunting` ドメイン (就活)
- **Web UI**: **Raspberry Pi** 上でホスティング（ADR-005）。k3s には載せない。
- **API / DB**: Windows 上の k3s Namespace `job-hunting`
- **役割**: ES・面接ログ・経験データの API。UI は Pi のフロントから Tailscale 経由で API を呼ぶ。
- **データ特性**: 高い整合性が必要（RDB: PostgreSQL）。
- **トラフィック**: インタラクティブ（人間によるブラウザ操作）。

### 1.2. `video-analysis` ドメイン (ゲーム動画解析)
- **Namespace**: `video-analysis`
- **役割**: プレイ／リプレイ動画の取り込み、ゲーム別セグメンテーション、単位クリップに対する AI メタデータ生成。
- **データ特性**: 大容量（動画ファイル、抽出画像、分割クリップ）。オブジェクトストレージまたは永続ボリューム（PV）に格納。
- **トラフィック**: バッチ処理型（Job / CronJob）。
- **内部構成（ゲーム別 pipeline）**: 共通層とタイトル固有層に分ける。最終的にワーカーを分散させることが前提（ADR-004）。

| 層 | 責務 | デプロイ単位の将来像 |
|----|------|----------------------|
| ingest（共通） | 動画受付、保存、`game` 種別の解決 | 共通サービスとして残しやすい |
| segmenter（ゲーム別） | カット点抽出とクリップ／セグメント分割 | `valorant-segmenter` / `tft-segmenter` 等 |
| analyzer（単位 Job） | 分割後の各単位に対する画像処理・Ollama 推論 | 並列度を制限した Job |
| sink（共通） | 解析結果を **video-analysis 専用 DB** に蓄積（`video-ingest-api`） | 就活 DB へは自動連携しない |

#### Valorant pipeline（Phase の最初の実装対象）
1. ラウンド間ロゴ（テンプレート）または遷移スパイクを検出し、カット点を抽出する。
2. そのカット点で動画を区切り、**ラウンドごとのプレイ動画**に分割する。
3. ラウンド単位クリップごとに analyzer Job を起動し、ホスト Ollama でメモを生成する。
4. 解析メモを sink し、ユーザーが **傾向の要約と上達 Tip** を受け取れるようにする（§2.1）。

カット検出の優先順位:
1. `Documents\HomeLLM\videos\templates\valorant\` の PNG/JPG テンプレート照合（OpenCV）
2. 明るいフラット画面／大きな場面変化（遷移スパイク）
3. 上記が空なら時間フォールバック（既定 90 秒）

analyzer:
- ラウンドごとにキーフレーム抽出 + Ollama（JSON）で facts / lessons / emotional / highlight
- 試合単位で詳細分析を再生成して `video_matches` に保存

#### 取り込み契約（ADR-008）

```
media/
  inbox/                 # Documents\HomeLLM\videos\inbox（ホストから見える）
  work/<jobId>/source.*  # 登録後に移動した原本
  rounds/<jobId>/        # ラウンド分割結果
  state/<jobId>.json     # 状態（queued|segmenting|ready|failed）
  done/ | failed/        # 事後整理用（任意）
```

| API | 内容 |
|-----|------|
| `POST /v1/jobs` | `{ "game": "valorant", "filename": "match.mp4" }` → job id。inbox にファイルが必須 |
| `GET /v1/jobs/{id}` | 状態・成果物パス |
| `GET /v1/jobs` | 一覧 |

- バイナリは HTTP で送らない。Pi はプロキシしない。
- 登録後、ingest API が `work/<jobId>/` へ move し、Valorant segmenter `Job` を起動する。
- カット点は OpenCV ロゴ検出 → 遷移スパイク → 時間フォールバック。
- analyzer はホスト Ollama（既定 `qwen3.5:9b`）でラウンド／試合メモを生成する。

#### Teamfight Tactics (TFT) pipeline（後続）1. **時間基準**でセグメントに分割する。
2. セグメント単位で分析 Job を起動する。

#### 実装フェーズ
- **Phase 1**: Windows の k3s に API + Postgres。Pi に最小 Web（またはプレースホルダ）。動画解析は未実装でも境界を前提に設計。
- **Phase 2**: Valorant pipeline（ingest → ロゴ検出分割 → ラウンド単位 AI Job → **video-analysis DB へ蓄積** → 傾向 / Tip）。
- **Phase 3**: TFT pipeline を同契約で追加。以降、タイトル追加は segmenter / 分析プロンプトの追加を基本とする。

#### Job 分割の目安
- ロゴ検出・時間分割などの前処理は CPU / OpenCV 寄り。
- 文言生成・高度な解釈はホスト Ollama（`qwen3.5:9b`）寄り。
- 前処理 Job と推論 Job を分離し、推論の同時実行数はホスト負荷を見て低く保つ（目安 1〜2）。

## 2. サービス間連携とAI（Ollama）アクセス
- **`job-hunting` と `video-analysis` は独立サービス**。DB・API・デプロイ単位を共有しない。Web UI は Tailscale 経由で **両 API を別々に** 呼ぶ。
- 動画解析の試合詳細・ハイライト・Tip は `video-analysis` 側（`docs/video_db_spec.md`）に完結する。
- 就活引き出しへゲーム知見を載せる場合は、将来 **ユーザー明示のエクスポート** を別機能とする（自動 sink しない）。
- **ローカルAI（Ollama）へのルーティング**:
  Windows 上の Pod は k3s の `ExternalName` またはホストゲートウェイ経由で、**同一 Windows ホスト**上の Ollama（`:11434`）へリクエストする。到達先ホスト名／IP の実体はローカル設定のみ（リポジトリには `<WINDOWS_OLLAMA_BASE_URL>` 等のプレースホルダ）。既定モデルは **`qwen3.5:9b`**。
- **フロント → API**: Pi 上の Web から Tailscale 経由で `job-hunting-api`（就活）と `video-ingest-api`（動画）を **別 URL** で呼ぶ。

## 2.1. 動画解析のプロダクト要件（Valorant 起点）

ユーザーが受け取りたい成果は「クリップが切れた」こと自体ではなく、次の体験である。

1. **試合（マッチ）単位の詳細分析**が残る（流れ・勝敗要因・全体の癖・次への課題。薄い一行要約では不足）
2. その試合の中で **特に注目すべきラウンド（ハイライト）** を一覧し、個別に見返せる
3. ラウンド単位の短いメモ（事実・反省・良かった点）も保存する（非ハイライトは UI で折りたたみ可）
4. 複数マッチを横断して **自分の傾向** がまとまる
5. その傾向に基づく **上達 Tip** を、ホスト Ollama から日本語で受け取れる

制約（就活 RAG と同じ思想）:

- クラウド LLM に動画・ログを送らない
- Tip 生成時にプロンプトへ入れるのは **厳選した短いテキストのみ**（試合詳細の全文ダンプや生 VOD は入れない）
- Tip は「一般論だけ」ではなく、蓄積した自分の解析メモを根拠にする

データフロー（要件）:

```text
inbox → segmenter → analyzer → video-ingest-api（matches/rounds DB）
                             → Web: 試合詳細 / ハイライト / Tip
```

蓄積先: `video-analysis` Namespace の Postgres（`docs/video_db_spec.md`）。

## 3. リソース制御戦略
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: video-analysis-quota
  namespace: video-analysis
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
```


**意図** : 重い画像処理・推論を行う video-analysis が暴走しても、job-hunting 側のPodが配置されているCPUコアやメモリ空間を侵食しないよう、k8sの ResourceQuota および LimitRange で物理的に上限を縛る。