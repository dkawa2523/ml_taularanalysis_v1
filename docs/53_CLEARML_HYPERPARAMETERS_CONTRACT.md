# ClearML: HyperParameters / Configuration 契約 v1

## 目的
- ClearML の **HyperParameters**（UI）を「再実行に必要な最小情報」で活用する。
- config_resolved.yaml を artifact に残す方針は維持しつつ、UI上でも主要設定が一目で分かるようにする。
- **冗長化防止**: 全 config を connect してノイズを増やさない。process ごとに抽出する。

## 設計方針
- `tabular_analysis/clearml/hparams.py` に抽出ロジックを集約
- `Task.connect(hparams_dict)` を使い HyperParameters をセット
- `Task.connect_configuration(mini_cfg_dict, name="effective")` で「要点だけ」の Configuration を補助的に出す（任意）

## 共通キー（全タスク）
- `usecase_id`
- `schema_version`
- `code_version`（取得できる場合）
- `clearml.execution`（logging/agent/pipeline_controller の区別）

## dataset_register（推奨）
- `data.dataset_path`（ローカル試験では有用。社内運用ではマスク/省略を検討）
- `data.target_column`

## preprocess（必須）
- `raw_dataset_id`（または dataset_path）
- `preprocess.variant`
- `split.strategy`, `split.seed`
- `processed_dataset.store_features`（true/false, config: `ops.processed_dataset.store_features`）

## train_model（必須）
- `processed_dataset_id`
- `task_type`
- `primary_metric`
- `model.variant`
- `model.params.*`（主要パラメータのみ）

## leaderboard（必須）
- `primary_metric`
- `direction`（maximize/minimize）
- `compare.require_comparable`
- `selection.top_k`

## infer（必須）
- `model_id`
- `infer.mode`
- `schema_policy`（strict/warn/coerce）
