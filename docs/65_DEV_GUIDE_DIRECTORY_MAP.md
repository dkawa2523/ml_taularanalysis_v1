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
  - `retrain.py`
- `conf/task/**`（task 名・stage・project の定義）
- `conf/task/<task>/**`（task の variant。例: `conf/task/pipeline/train_regression.yaml`）

## 2) モデル/前処理/特徴量
- `src/tabular_analysis/registry/models.py` / `src/tabular_analysis/registry/tabpfn.py`（モデル登録）
- `conf/group/model/`（モデル variant）
- `src/tabular_analysis/registry/preprocessors.py`（前処理登録）
- `conf/group/preprocess/`（前処理 variant）
- `src/tabular_analysis/feature_engineering/`（特徴量の生成/変換）
- `conf/group/split/`（split 方式）

### 2.1) Variant registry（pipeline v2 default の単一の正）
- `src/tabular_analysis/registry/variants.py` が preprocess/model/ensemble の default 候補と適用条件を定義する
- 新しい variant を追加する手順:
  - `conf/group/<group>/<id>.yaml` を追加し `<...>.name` を `<id>` と一致させる
  - `src/tabular_analysis/registry/variants.py` の registry に 1 エントリ追加
  - optional dependency は `requires=["xgboost"]` のように module 名で指定する
  - preprocess は numeric/categorical の applicability を追加する
- ID 命名規約: `snake_case` + conf ファイル名と一致（ensemble は `mean_topk/weighted/stacking`）
- default_enabled の基準: 安定・低コスト・optional 依存なしを基本に true、重い/optional は false

## 3) 評価・比較・品質
- `src/tabular_analysis/metrics/`（指標計算）
- `src/tabular_analysis/registry/metrics.py`（指標登録）
- `conf/leaderboard/`（スコアリング/推薦方針）
- `src/tabular_analysis/quality/data_quality.py` + `src/tabular_analysis/ops/data_quality.py`（品質ゲート）
- `docs/83_ENSEMBLE_POLICY.md`（アンサンブル比較の方針）

## 4) ClearML 統合 / UI / 命名
- `src/tabular_analysis/platform_adapter.py`（platform 依存の集約）
- `src/tabular_analysis/ops/clearml_identity.py`（usecase_id/tags/properties 生成）
- `src/tabular_analysis/clearml/`
  - `naming.py` / `hparams.py` / `ui_logger.py` / `templates.py` / `template_manager.py` / `datasets.py`
- `conf/run/base.yaml`（ClearML 実行モード）
- `conf/ops/clearml_policy/`（tags/properties ポリシー）
- `conf/clearml/templates.yaml`（テンプレートタスク定義）
- `docs/03_CLEARML_UI_CONTRACT.md` / `docs/61_CLEARML_HPARAMS_SECTIONS.md` / `docs/66_NAMING_TAGGING_POLICY.md`
- `docs/80_CLEARML_EXECUTION_MODES.md` / `docs/81_CLEARML_TEMPLATE_POLICY.md` / `docs/82_CLEARML_PROJECT_LAYOUT.md`

## 5) 可視化
- `src/tabular_analysis/viz/`（Plotly 生成）
- `docs/62_CLEARML_PLOTS_REGRESSION.md`

## 6) パイプライン / オーケストレーション
- `src/tabular_analysis/processes/pipeline.py`（entrypoint）
- `src/tabular_analysis/pipeline/driver_local.py`（local sequential）
- `src/tabular_analysis/pipeline/driver_controller.py`（PipelineController）
- `src/tabular_analysis/ops/local_orchestrator.py`（ローカル一括）
- `conf/pipeline/model_sets/`（model_set 定義）
- `conf/exec_policy/`（上限/選択ルール）

## 7) CLI / 検証 / リハーサル
- `src/tabular_analysis/cli.py`（Hydra CLI）
- `src/tabular_analysis/doctor.py` / `src/tabular_analysis/ops/ui_contract_lint.py`（検証）
- `docs/15_VERIFICATION.md` / `docs/16_OPERATIONS_RUNBOOK.md` / `docs/67_REHEARSAL_COMMANDS.md` / `docs/84_REHEARSAL_GUIDE.md`
- `tools/rehearsal/`（再現スクリプト）

## 8) 拡張ガイド（レビュー用ショートカット）
| 目的 | 触る場所 | 補足 |
| --- | --- | --- |
| registry（variant 追加） | `src/tabular_analysis/registry/variants.py` | default_enabled / requires / applicability をここで定義 |
| 新しいモデル追加 | `conf/group/model/<id>.yaml`<br>`src/tabular_analysis/registry/models.py`<br>`src/tabular_analysis/registry/variants.py` | docs は `docs/14_MODEL_CATALOG.md` を更新 |
| 新しい前処理追加 | `conf/group/preprocess/<id>.yaml`<br>`src/tabular_analysis/registry/preprocessors.py`<br>`src/tabular_analysis/feature_engineering/`<br>`src/tabular_analysis/registry/variants.py` | applicability 判定は SKIP ポリシーに影響 |
| 新しいアンサンブル追加 | `conf/ensemble/<method>.yaml`<br>`src/tabular_analysis/processes/train_ensemble.py`<br>`src/tabular_analysis/registry/variants.py` | 比較方針は `docs/83_ENSEMBLE_POLICY.md` |
| leaderboard ルール変更 | `conf/leaderboard/`<br>`src/tabular_analysis/processes/leaderboard.py` | report 表示は `docs/24_REPORTING.md` |
| pipeline plan/driver 変更 | `src/tabular_analysis/processes/pipeline.py`<br>`src/tabular_analysis/pipeline/driver_local.py`<br>`src/tabular_analysis/pipeline/driver_controller.py`<br>`conf/task/pipeline/base.yaml` | fail_policy/limits/parallelism は `conf/exec_policy/` と連動 |
| ClearML 表示（hparams/tags/projects/plots） | `src/tabular_analysis/clearml/hparams.py`<br>`src/tabular_analysis/clearml/naming.py`<br>`src/tabular_analysis/clearml/ui_logger.py`<br>`conf/clearml/hyperparams_sections.yaml`<br>`conf/clearml/project_layout.yaml` | 契約は `docs/03_CLEARML_UI_CONTRACT.md` / `docs/61_CLEARML_HPARAMS_SECTIONS.md` / `docs/66_NAMING_TAGGING_POLICY.md` / `docs/82_CLEARML_PROJECT_LAYOUT.md` |
