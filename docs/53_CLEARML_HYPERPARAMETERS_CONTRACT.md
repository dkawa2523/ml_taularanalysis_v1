# ClearML: HyperParameters / Configuration 契約 v2

## 目的
- ClearML の **HyperParameters**（UI）を「再実行に必要な最小情報」で活用する。
- config_resolved.yaml を artifact に残す方針は維持しつつ、UI上でも主要設定が一目で分かるようにする。
- **冗長化防止**: 全 config を connect してノイズを増やさない。抽出対象は conf で管理する。

## 設計方針
- 抽出ルールは `conf/clearml/hyperparams_sections.yaml`（`run.clearml.hyperparams.sections`）で定義する。
- `tabular_analysis/clearml/hparams.py` が dotpath から抽出し、`platform_adapter.init_task_context` が `Task.connect` で接続する。
- `Task.connect_configuration(mini_cfg_dict, name="effective")` は必要時のみ補助的に使う（任意）。

## 既定のキー（例）
- inputs: `run.usecase_id`, `run.output_dir`, `data.dataset_path`, `infer.mode` など
- dataset: `data.raw_dataset_id`, `data.processed_dataset_id`
- preprocess: `preprocess.*`, `data.split.*`, `ops.processed_dataset.*`
- model: `train.model`, `train.params`, `model_variant.*`
- eval: `eval.*`, `leaderboard.*`
- pipeline: `pipeline.*`
- clearml: `run.clearml.enabled`, `run.clearml.execution`, `run.clearml.code_ref.*` など

詳細は `docs/61_CLEARML_HPARAMS_SECTIONS.md` を参照。
