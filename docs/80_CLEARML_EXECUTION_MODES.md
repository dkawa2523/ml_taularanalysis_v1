# 80_CLEARML_EXECUTION_MODES（実行モードと切替ポイント）

## 目的
ClearML 実行モードの違いと、どの設定を触れば切り替えられるかを明確にする。
試験段階ではモードを固定しないが、**切替ポイントを明文化**して後で変更しやすくする。

## 実行モード一覧（要点）
### local
- 典型設定: `run.clearml.enabled=false` または `run.clearml.execution=local`
- 特徴: ClearML SDK を使わない。出力はローカルのみ。
- pipeline driver: **local_sequential**（ローカル逐次実行）
- 用途: 開発・デバッグの最速ループ

### logging
- 典型設定: `run.clearml.enabled=true` / `run.clearml.execution=logging`
- 特徴: ローカル実行だが ClearML に Task を記録する。
- pipeline driver: **local_sequential**（工程ごとに Task が記録される）
- 用途: UI 契約・Artifacts/Properties の確認

### agent
- 典型設定: `run.clearml.enabled=true` / `run.clearml.execution=agent`
- 特徴: `Task.execute_remotely(queue=...)` で投入。
- 注意: **pipeline は agent/clone を許可しない**（pipeline_controller を使う）

### clone
- 典型設定: `run.clearml.enabled=true` / `run.clearml.execution=clone`
- 特徴: テンプレ Task を clone して投入。
- 注意: **pipeline では使わない**（pipeline_controller を使う）

### pipeline_controller
- 典型設定: `run.clearml.enabled=true` / `run.clearml.execution=pipeline_controller`
- 特徴: PipelineController が子タスクを生成し、queue に投入。
- Controller 自体は agent 実行（queue が必要）。
- 子タスクは `execution=logging` 扱いで作られる。
- pipeline/子タスクとも **template clone** を必須にし、template_set + usecase_id をキーに解決する。
- plan は pipeline で先に生成し、driver（local_sequential / pipeline_controller）が **同一 plan** を使って実行する。
- controller task は commit pin を使わず branch を優先（template clone の再現性を維持）。

### pipeline_controller_local
- 典型設定: `run.clearml.enabled=true` / `run.clearml.execution=pipeline_controller_local`
- 特徴: controller はローカル実行、子タスクは queue に投入。
- 用途: controller のデバッグ（UI は pipeline_controller と近い）

## local_sequential と pipeline_controller の違い
- **local_sequential**: `src/tabular_analysis/pipeline/driver_local.py`。
  ローカル逐次で preprocess/train/leaderboard を実行し、必要なら ClearML に記録する。
- **pipeline_controller**: `src/tabular_analysis/pipeline/driver_controller.py`。
  ClearML 上でテンプレ clone を使って子タスクを生成し、Agent で実行する。
- どちらも **同一の plan** を使い、project/tags/hparams の見え方を揃える（plan は driver の前に生成）。

## どの yaml をどう切替えるか
- デフォルト設定: `conf/run/base.yaml`（`run.clearml.enabled` / `run.clearml.execution` / `run.clearml.queue_name`）
- 1 回限りの切替: CLI の Hydra override で上書き
- 恒常的な切替: `conf/run/<name>.yaml` を追加し `run=<name>` で選択

## 典型コマンド例（Python runner 含む）
### dataset_register（logging）
```bash
python -m tabular_analysis.cli task=dataset_register \
  run.clearml.enabled=true run.clearml.execution=logging \
  data.dataset_path=/tmp/ta_rehearsal_data/toy_reg.csv data.target_column=target
```

### pipeline（pipeline_controller / agent）
```bash
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default \
  data.raw_dataset_id=<RAW_DATASET_ID> \
  pipeline.preprocess_variant=stdscaler_ohe pipeline.model_set=regression_all
```

### ローカル（ClearML 無効）
```bash
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=false \
  data.raw_dataset_id=local:<HASH> data.dataset_path=/tmp/ta_rehearsal_data/toy_reg.csv \
  pipeline.preprocess_variant=stdscaler_ohe pipeline.model_set=regression_all
```

### Python runner（リハーサル用）
```bash
python tools/rehearsal/run_rehearsal.py --mode logging
python tools/rehearsal/run_train_pipeline.py --mode agent --queue-name default
```

## 変更ポイントまとめ（試験段階）
- `conf/run/base.yaml`: 実行モードの既定値
- `conf/clearml/templates.yaml`: clone/pipeline_controller のテンプレ定義
- `conf/exec_policy/base.yaml`: queue/上限の既定
- 仕様変更が必要なら `docs/10_OPERATION_MODES.md` と `docs/52_CLEARML_PIPELINE_CONTROLLER_CONTRACT.md` を更新
