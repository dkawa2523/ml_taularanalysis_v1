# 82_CLEARML_PROJECT_LAYOUT（Project 階層と変更ポイント）

## 目的
ClearML の Project 階層を **config-driven** で統一し、
試験段階でも後から構成を変更しやすくする。

## ルール（基本形）
`<ROOT>/<solution_root>/<usecase_id>/<process_group>`

- ROOT: `run.clearml.project_root`（環境変数 `TABULAR_ANALYSIS_CLEARML_PROJECT_ROOT` で上書き可）
- solution_root: `run.clearml.project_layout.solution_root`
- usecase_id: `run.usecase_id`（未指定なら `run.usecase_id_policy` が生成）
- process_group: `run.clearml.project_layout.group_map[process]`（未定義は `misc_group`）
- 設定ファイル: `conf/clearml/project_layout.yaml`

例（デフォルト）:
- `MFG/TabularAnalysis/test_toy_20260101_120000/01_Datasets`
- `MFG/TabularAnalysis/test_toy_20260101_120000/02_Preprocess`
- `MFG/TabularAnalysis/test_toy_20260101_120000/03_TrainModels`
- `MFG/TabularAnalysis/test_toy_20260101_120000/04_Ensembles`
- `MFG/TabularAnalysis/test_toy_20260101_120000/05_Infer`
- `MFG/TabularAnalysis/test_toy_20260101_120000/00_Pipelines`（leaderboard もここに配置）
- `MFG/TabularAnalysis/test_toy_20260101_120000/00_Pipelines`

## どこを変更するか
### 1) 全体のルート（組織/部門）
- `conf/run/base.yaml`: `run.clearml.project_root`
- または環境変数: `TABULAR_ANALYSIS_CLEARML_PROJECT_ROOT`

### 2) solution_root / process_group
- `conf/clearml/project_layout.yaml`
  - `solution_root`
  - `group_map`（process -> group）
  - `misc_group`（未定義プロセスの受け皿）
  - `separator`

### 3) テンプレ Task の配置
- `conf/clearml/templates.yaml` は `project_root/usecase_id/...` を別途定義している。
- Project 階層を変える場合、テンプレ側の `project_name` も合わせて更新する。

## 試験段階の運用（固定しない）
- UI で迷わない構成を試すため、`docs/43_CLEARML_UI_LAYOUT_EXAMPLES.md` の案を回して比較する。
- 比較結果は `docs/issues/ISSUE_PROJECT_HIERARCHY.md` などに記録する。

## 変更ポイントまとめ
- `conf/run/base.yaml`: project_root
- `conf/clearml/project_layout.yaml`: solution_root / group_map
- `conf/clearml/templates.yaml`: template project の整合
- UI 契約を変える場合は `docs/03_CLEARML_UI_CONTRACT.md` を更新
