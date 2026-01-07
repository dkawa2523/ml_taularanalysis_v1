# T058 PipelineController 実装（子タスク生成・grid実行）

## Objective
`run.clearml.execution=pipeline_controller` を実装し、ClearML PipelineControllerで各工程タスクを生成・実行できるようにする。

## Risk / Redundancy check (read before coding)
- 変更は **ClearML統合の薄い層**（`src/tabular_analysis/clearml/`）へ集約し、process側に重複ロジックを散らさない。
- HyperParameters/Configuration は **最小**。全文connect禁止（UIがノイズで死ぬ）。
- local pipeline と pipeline_controller の仕様二重化を避ける（plan/step定義を共通化）。

## Context / Why
pipeline実行が1タスクに留まり、controllerによる子タスク生成ができないと運用で追跡・比較が困難。ClearMLの機能を最大活用し、grid実行もUI上で追える形にする。

## Instructions (do exactly)
1. `src/tabular_analysis/processes/pipeline.py` を改修し、execution=pipeline_controller の分岐を追加（loggingでは子タスクを作らない仕様のまま）。
2. 二重実装を避けるため、pipelineの仕様（どのstepをどう繋ぐか）を `pipeline_plan` のような関数/クラスに集約し、
   - local実行: planを順次実行
   - controller実行: planから PipelineController steps を生成
   の形にする（“仕様は1つ”）。
3. ClearML `PipelineController` で steps:
   - dataset_register
   - preprocess（preprocess_variantsを展開）
   - train_model（preprocessごとのprocessed_dataset_idに依存。model_variantsを展開）
   - leaderboard（train task idsを入力として渡す）
   - infer（推奨モデルが必要なら optional。まずは off でOK）
4. 子タスクは template task clone 方式:
   - `tabular_analysis/clearml/templates.py` を新設し、tags検索でtemplateを取得
   - templateが無い場合は明確にエラー（T059のツールを案内）
5. grid tags:
   - `grid_run_id` を全子タスクにつける
   - trainには `grid_cell:<preprocess>__<model>` をつける
6. orchestrator は pipeline_run.json（子タスクID一覧）を artifact に保存し、Scalarsに成功/失敗数を出す（docs/51）。
7. 子タスクの HyperParameters は docs/53 準拠で connect（hparams.py）。
8. docs/52 を更新


## Acceptance Criteria
- pipeline_controller モードで実行すると、ClearML UI に dataset_register / preprocess / train_model / leaderboard の複数Taskが生成される。
- grid指定で train task が複数作られる（例: 2モデル × 1前処理 = 2タスク）。
- orchestrator は pipeline_run.json と Scalars（成功/失敗数）を出す。


## Verification (run locally)
```bash
python -m compileall -q src
# 手動確認（ローカルClearML + agent起動が必要）
# clearml-agent daemon --foreground --queue default --create-queue
# python -m tabular_analysis.cli task=pipeline/base run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default data.dataset_path=/tmp/ta_rehearsal_data/toy_cls.csv data.target_column=target pipeline.grid.model_variants='[logistic_regression,random_forest]' pipeline.grid.preprocess_variants='[stdscaler_ohe]'

```

## Result
- RESULT: TODO (nonce: <fill>)
