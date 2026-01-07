# T042 ClearML テンプレ Task 運用の標準化（clone運用の安定化）

## Objective
- ClearML UI から「Cloneして実行」する運用を **標準化**し、誰が実行しても project/entrypoint/config が正しくなる状態を作る
- ClearML が使えない環境でも、テンプレ生成の **plan（設計書）** が作れるようにする（apply は optional）

---

## Constraints
- ClearML API が使えない（資格情報が無い）環境でも verify が通ること
- テンプレ task の乱立で UI が汚れないよう、用途別の project と命名を統一する
- ml-platform を変更しない。Solution 側でテンプレ運用ツールを実装する

---

## Scope
### 1) テンプレ定義（spec）を YAML で管理
- 例：`conf/clearml/templates.yaml`（または `conf/run/clearml_templates.yaml`）
  - dataset_register / preprocess / train_model / infer / leaderboard / pipeline / promote_model / rollback_model / champion_challenger / retrain など
  - 各テンプレに：
    - `project_name`
    - `task_name_template`
    - `entrypoint`（例：`python -m tabular_analysis.cli task=train_model`）
    - `default_overrides`（Hydra override の最小セット）
    - `tags`（usecase/process など必須タグ）
    - `properties_minimal`（検索用の最小プロパティ）
  - ※「詳細設定」は template に入れず、ユーザーがClone後に必要な override だけ変える

### 2) template 管理 CLI（plan/apply）
- 新規スクリプト例：`tools/clearml_templates/manage_templates.py`
  - `--plan`：テンプレ一覧と実行手順を `artifacts/template_plan.json` と `template_plan.md` に出力（ClearML不要）
  - `--apply`：ClearML が有効な場合のみ template task を作成し、template_task_id を `conf/clearml/templates.lock.yaml` に書く（既存があれば再利用）
  - `--validate`：lock の task_id が存在するか確認（ClearML利用時のみ）

### 3) docs
- `docs/21_CLEARML_TEMPLATE_TASKS.md` を追加し、以下を明記：
  - テンプレの目的
  - 作成手順（plan/apply）
  - template_task_id の保管場所（lockファイル）
  - Clone 実行時にユーザーが触るのは “override” のみ、というルール

---

## Acceptance Criteria
- `--plan` が ClearML 無しで動き、テンプレ一覧が生成される
- `--apply` は ClearML 資格情報がある場合のみ動作し、無い場合は明確に skip できる
- テンプレの定義が docs と一致している
- verify は ClearML 無しで通る（plan + schemaチェック）

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_template_specs.py
```
