# Local実行＋SPDML結果登録の各タスクの利用方法

## 1. コマンド一覧
| タスク | コマンド | 主な設定ファイル | tips |
| --- | --- | --- | --- |
| dataset_register | `python -m tabular_analysis.cli task=dataset_register run.clearml.enabled=true run.clearml.execution=logging data.dataset_path=...` | `conf/task/dataset_register/base.yaml` | `out.json` の raw_dataset_id を控える |
| pipeline | `python -m tabular_analysis.cli task=pipeline run.clearml.enabled=true run.clearml.execution=logging data.raw_dataset_id=... pipeline.model_set=regression_all` | `conf/task/pipeline/base.yaml` | `pipeline.grid.*` で上限制御 |
| infer (single) | `python -m tabular_analysis.cli task=infer infer.mode=single run.clearml.enabled=true run.clearml.execution=logging infer.model_id=... infer.input_path=...` | `conf/task/infer/base.yaml` | 入力列の順序と型に注意 |
| local_orchestrator | `python -m tabular_analysis.ops.local_orchestrator train_regression --dataset-path ... --preprocess stdscaler_ohe --model-set regression_all --clearml` | `conf/task/*` | SPDMLに複数タスクを自動生成 |

## 2. tips
- `run.clearml.execution=logging` は**ローカル実行しつつSPDMLに記録**するモード。
- `pipeline` は `data.raw_dataset_id` が必須。dataset_register を先に実行する。
- `pipeline.grid.model_variants=[ridge,lasso]` のように Hydra list 形式で指定する。
- 大量モデルは `exec_policy.limits.max_jobs` で制限する。
