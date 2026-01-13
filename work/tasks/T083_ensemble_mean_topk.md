# T083 [HOTFIX] アンサンブル（mean_topk）: 失敗/重いモデルを安全にスキップしつつ「学習候補」として比較評価できるようにする

## 背景
- アンサンブルは **推論で常用しない**（精度が分からないまま合成したくない）
- よって **アンサンブルも「学習済みモデル候補の1つ」**として作り、leaderboard で単体モデルと同列比較したい
- ただし TabPFN / GaussianProcess / SVR / SVC 等は **失敗しやすい/重い/確率が揃わない** ことがあるため、ensemble 側での **候補フィルタ・スキップ記録**が必須

---

## 目的
- `process:train_ensemble` を追加（method=mean_topk）
- **成功した base train_model のみ**を候補にし、失敗/不整合は **スキップして理由を記録**
- leaderboad が **単体 + ensemble** を同列に比較できる（metrics/manifest/spec が揃う）

---

## 重要な設計（このタスクで必ず入れる）

### 1) 「候補モデル選定」は決定的＆安全
候補条件（すべて満たすもののみ採用）:
- `process:train_model` である
- `status==completed` 相当（ClearML enabled なら Task.status、ローカルなら out.json に success）
- `usecase:<usecase_id>` が一致
- `preprocess_variant` が一致（同一 preprocess 内でのみ ensemble）
- metric が取得できる（`eval.primary_metric` の値がある）
- **検証予測が取得できる**（下の「予測artifact契約」）

不採用（skip）にする条件:
- 失敗・中断・invalid
- 予測artifactが無い
- task_type と予測形式が合わない（分類で確率が必要なのに無い等）
- `ensemble.exclude_variants` に含まれる

> 重要: 不採用でも pipeline 全体を落とさない（= degraded success）。

### 2) 予測artifactの「契約」を明文化し、取れない場合はスキップ（fallbackは明示的オプション）
**基本方針**: ensemble は「再推論」をしない（重い＆不安定）。

train_model の出力契約（追加/強化）:
- 回帰: `preds_valid.parquet`（最低限: `y_true`, `y_pred`）
- 分類: `preds_valid.parquet`（最低限: `y_true`, `proba__<class>` 列）
  - 併せて `classes.json`（class順）を出す

ensemble 側は上記を **まず探す**。
- ない場合は **原則スキップ**し、理由に `missing_preds_valid` を記録
- ただし試験段階での互換のため、`ensemble.fallback_rerun_predict: true` のときのみ
  - model_bundle から再推論して preds_valid を作ってよい（重いので default false）

### 3) スキップ理由は必ず残す（運用で最重要）
`ensemble_spec.json` に以下を保存:
- `method: mean_topk`
- `selection_metric`, `direction`
- `top_k`
- `preprocess_variant`
- `included`: [{train_task_id, model_variant, metric_value, preds_ref}]
- `skipped`: [{train_task_id, model_variant, reason, details?}]
- `created_at`, `code_version`, `schema_version`

ClearML enabled の場合は `ensemble_spec.json` を artifact として upload。

### 4) 受け入れ基準を「壊れない」ものにする
- 候補が0件 → **task は failed（理由: no_valid_base_models）**
- 候補が1件以上 → ensemble を作り、**一部スキップがあっても成功**

---

## 変更内容（実装）

### A) config 追加
- `conf/ensemble/base.yaml`（新設 or 既存拡張）
  - `ensemble.enabled: true/false`
  - `ensemble.method: mean_topk`（T084/T085で拡張）
  - `ensemble.top_k: 3`
  - `ensemble.selection_metric: ${eval.primary_metric}`
  - `ensemble.exclude_variants: []`（例: ["gaussian_process", "svr"]）
  - `ensemble.fallback_rerun_predict: false`

### B) train_model の出力を ensemble 契約に合わせる（最小追加）
- 既に出している場合は「存在確認＋スキーマ統一」だけ行う
- 追加が必要な場合:
  - `preds_valid.parquet` を `out_dir/artifacts/` に保存
  - 分類では `classes.json` を保存
  - out.json に `preds_valid_path` / `preds_schema` を記録
  - ClearML enabled なら artifact upload

> 注意: TabPFN 等が失敗する場合でも、train_model 自体の失敗は許容。ensemble が落ちないことが目的。

### C) 新規: `process:train_ensemble`（mean_topk）
- 入力（最小）:
  - `run.usecase_id`
  - `preprocess.variant`
  - `ensemble.*`
- Discovery:
  - ClearML enabled: tags/usecase/preprocess/process で train_model を収集
  - ClearML disabled: out_dir を走査して train_model の out.json を収集
- 選定:
  - metric で top_k 選定（maximize/minimize は metric registry で決定）
  - 候補不足なら top_k を下げる（ただし 0 なら fail）
- 合成:
  - 回帰: `y_ens = mean(y_pred)`
  - 分類: **確率平均**（classes順を必ず合わせる）
- 評価:
  - eval モジュールと同じ指標セットで metrics.json を作る
- 出力:
  - `ensemble_spec.json`
  - `metrics.json`
  - `model_bundle`（推論で 1 model_id として扱える形）
    - 方式: 「base model ids + 合成方式」を bundle に保持し、infer で復元・合成
  - `manifest.json` の hashes に `config_hash` / `split_hash` / `recipe_hash` を必ず含める（skip 時も同様）

### D) ClearML 表示
- task name: `train_ensemble/mean_topk(k=3)` のように識別可能
- tags:
  - `process:train_ensemble`
  - `model:ensemble_mean_topk`
  - `ensemble:mean_topk`
  - `topk:3`
  - `preprocess:<variant>`
- Scalars:
  - primary_metric + 主要指標
- Plots:
  - 「included base models table」（Plotly table）
  - 「skipped reasons summary」（小さなtableで十分）

---

## 受け入れ基準（Acceptance Criteria）
- mean_topk ensemble が “学習候補タスク” として作成される
- base model が一部失敗/重い/確率不整合でも、**スキップして task は成功**できる（候補>=1の場合）
- `ensemble_spec.json` に included/skipped が記録される
- leaderboard が同列比較できるための metrics/manifest が揃う

---

## テスト
- `python -m compileall -q src`
- toy データで:
  - preprocess 1種 + train 複数モデル（うち1つは意図的に落としても良い）
  - ensemble_mean_topk → leaderboard
  - ensemble が落ちずに `skipped` を記録していること
