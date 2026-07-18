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
| sink（共通） | 結果テキスト／メタデータを `job-hunting` へ渡す | 内部 API またはイベント |

#### Valorant pipeline（Phase の最初の実装対象）
1. ラウンド間にのみ出現するロゴを識別し、カット点を抽出する。
2. そのカット点で動画を区切り、**ラウンドごとのプレイ動画**に分割する。
3. ラウンド単位クリップごとに AI Job を起動する。

#### Teamfight Tactics (TFT) pipeline（後続）
1. **時間基準**でセグメントに分割する。
2. セグメント単位で分析 Job を起動する。

#### 実装フェーズ
- **Phase 1**: Windows の k3s に API + Postgres。Pi に最小 Web（またはプレースホルダ）。動画解析は未実装でも境界を前提に設計。
- **Phase 2**: Valorant pipeline（ingest → ロゴ検出分割 → ラウンド単位 AI Job → sink）。
- **Phase 3**: TFT pipeline を同契約で追加。以降、タイトル追加は segmenter / 分析プロンプトの追加を基本とする。

#### Job 分割の目安
- ロゴ検出・時間分割などの前処理は CPU / OpenCV 寄り。
- 文言生成・高度な解釈はホスト Ollama（`qwen3.5:9b`）寄り。
- 前処理 Job と推論 Job を分離し、推論の同時実行数はホスト負荷を見て低く保つ（目安 1〜2）。

## 2. サービス間連携とAI（Ollama）アクセス
- **非同期連携**: 動画解析が完了して抽出されたテキストデータ（「このシーンでの反省点」など）は、バックエンドの内部API（またはイベント）を経由して `job-hunting` のデータベースに蓄積され、「引き出し」の一部となる。
- **ローカルAI（Ollama）へのルーティング**:
  Windows 上の Pod は k3s の `ExternalName` またはホストゲートウェイ経由で、**同一 Windows ホスト**上の Ollama（`:11434`）へリクエストする。到達先ホスト名／IP の実体はローカル設定のみ（リポジトリには `<WINDOWS_OLLAMA_BASE_URL>` 等のプレースホルダ）。既定モデルは **`qwen3.5:9b`**。
- **フロント → API**: Pi 上の Web から Tailscale 経由で Windows の `job-hunting-api` Service を呼ぶ。

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