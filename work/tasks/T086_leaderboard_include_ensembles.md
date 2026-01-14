# T086 [HOTFIX] leaderboard 拡張: 単体 + アンサンブル（mean/weighted/stacking）を同列表示しつつ、比較不能ケースを安全に運用

## 背景
- leaderboard の目的は「推論に利用すべきモデル選定」
- アンサンブル（mean/weighted/stacking）も **学習候補**として比較したい
- ただし stacking は `primary_metric_source` が `test`/`meta_cv_on_valid` など混在し得る
  → **表示は同列**にしつつ、**推薦(recommend)は比較ルールを明示**して事故を防ぐ

---

## 目的
- 収集対象を拡張（`process:train_model` + `process:train_ensemble`）
- 1行の標準スキーマに正規化し、比較テーブルを生成
- 推薦ロジックは config で制御し、metric_source 混在時のルールを明文化

---

## 実装方針（必須要件）

### 1) 収集とスキップは「落とさない」
- 収集時に壊れたタスク（metrics欠損/manifest欠損/途中失敗）を見つけても leaderboard 自体は落とさない
- 代わりに `leaderboard_skipped.json` を artifact として保存（どれを、なぜ除外したか）

### 2) 標準スキーマ（行）
最低限以下の列を必ず持つ（csv/json両方でOK）:
- `model_family`: `single` | `ensemble`
- `model_variant`: `ridge` / `lgbm` / `ensemble_mean_topk` / `ensemble_weighted` / `ensemble_stacking` ...
- `preprocess_variant`
- `primary_metric`: 数値
- `primary_metric_source`: `valid` | `test` | `meta_cv_on_valid` | `unknown`
- `metrics.*`: r2/rmse/mae...（取れるものだけ）
- `train_task_id`
- `model_id`（または model_ref）
- `n_base_models`（ensembleのみ）
- `ensemble_method`（ensembleのみ）

### 3) metric_source 混在へのルール（重要）
- leaderboard は **表示としては混在OK**（列で source を明示）
- ただし recommend はデフォルトで **単一の metric_source に限定**する（事故防止）

推奨の config:
- `leaderboard.recommend.metric_source_priority: ["test", "valid", "meta_cv_on_valid"]`
- `leaderboard.recommend.allow_cross_metric_source: false`（デフォルト）
  - false の場合: priority の先頭から「候補が1件以上ある source」を選び、その source だけで順位付けして推薦
  - true の場合: source 混在のまま順位付け（試験段階では非推奨）

### 4) ensemble の推薦をコントロール
- `leaderboard.recommend.allow_ensemble: true/false`
- `leaderboard.recommend.tie_breaker: prefer_simple|prefer_stable`
  - prefer_simple: 同点なら single を優先

### 5) ensemble の詳細は artifact に寄せ、properties は最小に
- properties は検索用最小キー（usecase / preprocess / model_variant / metric / source）
- ensemble の内訳（included/skipped/weights/base ids）は `ensemble_spec.json` を参照

---

## 変更内容（実装）

### A) leaderboard の収集対象
ClearML enabled:
- tags で取得
  - `usecase:<usecase_id>`
  - `process:train_model` または `process:train_ensemble`
  - （あれば）`grid:<grid_id>`

ClearML disabled:
- out_dir を走査して manifest/out.json を集める

### B) metrics の取り扱い
- 各タスクから `metrics.json` を読み込む
- primary_metric は `eval.primary_metric` を基本に
- もし `primary_metric_source` が out/spec にあるならそれを採用
  - train_ensemble は T083〜T085 で `primary_metric_source` を spec に入れている前提
  - train_model 側に無い場合は `valid` 扱いでよい

### C) ClearML 可視化（過剰にしない）
- Plots:
  - ranking table（Plotly Table）
  - primary_metric bar（上位Nのみ）
  - 追加は `run.clearml.logging.level` でON/OFF
- Scalars:
  - `best/primary_metric`
  - `best/model_variant`
  - `best/metric_source`

### D) 推薦結果の出力
- `decision_summary.json`（既存契約に合わせる）
  - recommended_train_task_id
  - recommended_model_id
  - recommended_reason（metric/source/allow_ensemble等）
- `leaderboard.csv`（表示用）
- `leaderboard_skipped.json`（除外理由）

---

## 受け入れ基準（Acceptance Criteria）
- leaderboard が単体+ensemble を同一テーブルに載せられる
- metric_source が列として明示される
- recommend はデフォルトで単一 metric_source のルールで安定して動く
- 壊れた/欠損タスクがあっても leaderboard が落ちず、skipped が残る

---

## テスト
- `python -m compileall -q src`
- toy データで:
  - train_model 複数 + ensemble 複数 → leaderboard
  - `leaderboard.csv` に single/ensemble 両方が載る
  - `leaderboard_skipped.json` が生成される（意図的に1つ欠損させても良い）

---

## Update (2026-01-13)
- `train_ensemble` / `primary_metric_source` が未実装のため後段対応
- refactor plan の Phase 3 (T101) で実装予定
