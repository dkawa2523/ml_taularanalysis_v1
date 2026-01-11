# ClearML: Pipeline Controller 実装契約 v2

## 問題
`pipeline` を実行しても「pipeline という名前の Task だけ」になり、各工程の Task が作成されない。

## 目的
- ClearML の **PipelineController** を使って、dataset_register / preprocess / train_model / leaderboard / infer を **別Taskとして生成・実行**する。
- 複数モデル学習（grid）を controller で束ね、UI上で追跡しやすくする。
- **設計の冗長化を防ぐ**: local pipeline と controller pipeline の“仕様”を共通化し、分岐だけで動くようにする。

## 実行モード
- `run.clearml.execution=pipeline_controller` を追加し、このモードのとき:
  - pipeline task は controller の orchestrator としてのみ動く
  - 子タスク群が ClearML 上に作成され、queue に投入される
- `execution=logging` は「ローカル実行 + 記録」なので子タスクは作られない（仕様）

## 子タスク作成方針（試験段階）
- 原則: template task を clone してパラメータを上書き（UI運用に近い）
- template 探索:
  - tags: `template:true` AND `process:<dataset_register|preprocess|train_model|leaderboard|infer>`
- template が無い場合:
  - 明確にエラー（「テンプレ作成ツールを先に実行せよ」を表示）

## grid 実行
- preprocess_variants を展開し、各 preprocess の出力 `processed_dataset_id` に依存する train を作成
- model_variants を展開し、train tasks を並列に
- tags:
  - `grid_run_id`
  - `grid_cell:<preprocess>__<model>`

## Orchestrator 出力
- pipeline task は `pipeline_run.json` を artifact に残し、子タスクIDの参照を保持する
- Scalars:
  - `pipeline/num_models`
  - `pipeline/num_succeeded`
  - `pipeline/num_failed`

## Hyperparameters / Configuration
- 子タスクは `clearml/hparams.py` を使い、UIの HyperParameters に「最低限の再現情報」を載せる（詳細は docs/53）。
