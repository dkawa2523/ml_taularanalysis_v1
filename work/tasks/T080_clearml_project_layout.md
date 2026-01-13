# T080 ClearML の Project 階層を自動階層化（configで容易に変更可能に）

## 背景（要求）
- pipeline で複数前処理 × 複数モデルを並列実行すると Task 数が一気に増え、ClearML UI が見づらくなる
- Project を `<root>/TabularAnalysis/<usecase_id>/<process_group>` に階層化し、探索性を上げたい
- ただし不特定の開発者が容易に変更できるように **config駆動**にする

---

## 目的
- Project 階層の規約を 1箇所に集約し、Local/Agent で統一
- process が増えても “どこに置くか” が一貫し、運用が破綻しない
- 開発者が `conf/` を編集すれば階層を変えられる

---

## 実装方針
### 1) project layout 用の設定を追加
例: `conf/clearml/project_layout.yaml`（新設でも既存でもOK）

- `run.clearml.project_layout.solution_root`: `"TabularAnalysis"`（固定文字列）
- `run.clearml.project_layout.group_map`:
  - `dataset_register: "01_Datasets"`
  - `preprocess: "02_Preprocess"`
  - `train_model: "03_TrainModels"`
  - `train_ensemble: "04_Ensembles"`
  - `infer: "05_Infer"`
  - `leaderboard: "06_Leaderboards"`
  - `pipeline: "00_Pipelines"`
  - `promote_model: "07_Promote"`
- `run.clearml.project_layout.separator`: `"/"`（通常固定）

### 2) “project path builder” を追加して全箇所で利用
例: `src/tabular_analysis/clearml/project_layout.py` のような小モジュールを追加:

- `build_project_path(cfg, process_name: str, usecase_id: str) -> str`
  - `<project_root>/<solution_root>/<usecase_id>/<group>` を返す
  - `project_root` は既存 `run.clearml.project_root` を使用
  - 未定義の process は `Misc` に落とす（落ちない設計）

### 3) Task.init / set_project などの呼び出しを統一
- pipeline_controller driver
- local_sequential driver
- 単体タスク実行（preprocess/train/leaderboard/infer など）

**禁止**:
- コード内で `"TabularAnalysis"` や `"03_TrainModels"` を直書きすること（全部 config）

---

## 受け入れ基準（Acceptance Criteria）
- 主要 process の Task が `<root>/TabularAnalysis/<usecase_id>/<process_group>` に配置される
- config の group 名を変えると Project の作られ方が変わる（コード修正不要）
- `python -m compileall -q src` が通る

---

## テスト
- `python -m compileall -q src`
- （ClearML接続あり）dataset_register → preprocess → train の順に実行し、Project 階層が揃っていることを UI で確認
