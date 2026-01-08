# 開発者ガイド：どこを見て直すか v2

## 目的
開発者が目的別に「見るべきディレクトリ/ファイル」を即座に特定できるようにする。

## 0) 入口
- `docs/INDEX.md`（全体の入口）
- `docs/03_CLEARML_UI_CONTRACT.md`（ClearML UI 契約）
- `docs/66_NAMING_TAGGING_POLICY.md`（命名/タグ/Properties の単一の正）

## 1) タスク実装（各プロセス）
- `src/tabular_analysis/processes/`（実装の入口）
  - `dataset_register.py` / `preprocess.py` / `train_model.py` / `leaderboard.py` / `infer.py` / `pipeline.py`
  - `champion_challenger.py` / `promote_model.py` / `retrain.py` / `rollback_model.py`
- `conf/task/**`（task 名・stage・project の定義）
- `conf/task/<task>/**`（task の variant。例: `conf/task/pipeline/train_regression.yaml`）

## 2) モデル/前処理/特徴量
- `src/tabular_analysis/registry/models.py` / `src/tabular_analysis/registry/tabpfn.py`（モデル登録）
- `conf/group/model/`（モデル variant）
- `src/tabular_analysis/registry/preprocessors.py`（前処理登録）
- `conf/group/preprocess/`（前処理 variant）
- `src/tabular_analysis/feature_engineering/`（特徴量の生成/変換）
- `conf/group/split/`（split 方式）

## 3) 評価・比較・品質
- `src/tabular_analysis/metrics/`（指標計算）
- `src/tabular_analysis/registry/metrics.py`（指標登録）
- `conf/leaderboard/`（スコアリング/推薦方針）
- `src/tabular_analysis/quality/data_quality.py` + `src/tabular_analysis/ops/data_quality.py`（品質ゲート）

## 4) ClearML 統合 / UI / 命名
- `src/tabular_analysis/platform_adapter.py`（platform 依存の集約）
- `src/tabular_analysis/ops/clearml_identity.py`（usecase_id/tags/properties 生成）
- `src/tabular_analysis/clearml/`
  - `naming.py` / `hparams.py` / `ui_logger.py` / `templates.py` / `template_manager.py` / `datasets.py`
- `conf/run/base.yaml`（ClearML 実行モード）
- `conf/ops/clearml_policy/`（tags/properties ポリシー）
- `conf/clearml/templates.yaml`（テンプレートタスク定義）
- `docs/03_CLEARML_UI_CONTRACT.md` / `docs/61_CLEARML_HPARAMS_SECTIONS.md` / `docs/66_NAMING_TAGGING_POLICY.md`

## 5) 可視化
- `src/tabular_analysis/viz/`（Plotly 生成）
- `docs/62_CLEARML_PLOTS_REGRESSION.md`

## 6) パイプライン / オーケストレーション
- `src/tabular_analysis/processes/pipeline.py`（local + PipelineController）
- `src/tabular_analysis/ops/local_orchestrator.py`（ローカル一括）
- `conf/pipeline/model_sets/`（model_set 定義）
- `conf/exec_policy/`（上限/選択ルール）

## 7) CLI / 検証 / リハーサル
- `src/tabular_analysis/cli.py`（Hydra CLI）
- `src/tabular_analysis/doctor.py` / `src/tabular_analysis/ops/ui_contract_lint.py`（検証）
- `docs/15_VERIFICATION.md` / `docs/16_OPERATIONS_RUNBOOK.md` / `docs/67_REHEARSAL_COMMANDS.md`
- `tools/rehearsal/`（再現スクリプト）
