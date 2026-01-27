# SPDMLAgent結果登録の各タスクの利用方法

## 1. コマンド一覧
| タスク | コマンド | 主な設定ファイル | tips |
| --- | --- | --- | --- |
| テンプレ作成 | `python -m tabular_analysis.ops.manage_clearml_templates --apply` | `conf/clearml/templates.yaml` | 先にテンプレを用意 |
| pipeline_controller | `python -m tabular_analysis.cli task=pipeline run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default data.raw_dataset_id=...` | `conf/task/pipeline/base.yaml` | queue必須 |
| dataset_register | `python -m tabular_analysis.cli task=dataset_register run.clearml.enabled=true run.clearml.execution=agent run.clearml.queue_name=default data.dataset_path=...` | `conf/task/dataset_register/base.yaml` | Agent起動確認 |
| infer | `python -m tabular_analysis.cli task=infer infer.mode=single run.clearml.enabled=true run.clearml.execution=agent run.clearml.queue_name=default infer.model_id=...` | `conf/task/infer/base.yaml` | input_pathを指定 |

## 2. tips
- `run.clearml.queue_name` が未設定だと enqueue できない。
- template clone では `run.clearml.code_ref.mode=branch` が推奨。
- `pipeline_controller` は child tasks を logging扱いで生成する。
