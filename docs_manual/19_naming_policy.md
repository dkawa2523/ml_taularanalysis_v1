# 命名・タグ・プロジェクト階層ルール

## タスク名（要点）
- 既定: process 名（`dataset_register` / `preprocess` / `train_model` / `leaderboard` / `infer` / `pipeline` / `retrain`）
- `run.clearml.task_name` が指定されれば優先
- preprocess / train_model / infer 子タスクは自動命名ルールあり（`docs/66_NAMING_TAGGING_POLICY.md`）

## Tags / Properties
- 主要タグ: `usecase:<id>`, `process:<process>`, `schema:<version>` など
- 追加タグは `run.clearml.extra_tags` で指定
- Properties は最小キーのみ（詳細は artifact へ）

## プロジェクト階層
`conf/clearml/project_layout.yaml` で統一:
- `dataset_register`: `01_Datasets`
- `preprocess`: `02_Preprocess`
- `train_model`: `03_TrainModels`
- `train_ensemble`: `04_Ensembles`
- `infer`: `05_Infer`
- `infer_child`: `05_Infer_Children`
- `leaderboard` / `pipeline`: `00_Pipelines`
