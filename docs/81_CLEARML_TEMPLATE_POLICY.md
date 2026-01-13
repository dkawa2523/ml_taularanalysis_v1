# 81_CLEARML_TEMPLATE_POLICY（テンプレ運用と切替ポイント）

## 目的
テンプレ Task は local/logging では必須ではないが、clone/pipeline_controller で
**見え方一致を保つために必須**である。将来の運用を見据えて
作成/更新/切替のやり方を明文化し、テンプレ増殖を避けるために
`template_set_id` を使って世代管理する。

## 用語と意味
- `run.clearml.template_usecase_id`
  - テンプレ Task の `usecase_id`。テンプレを置く専用領域を分離する。
  - 例: `TabularAnalysis`（テンプレ専用の usecase）
- `run.clearml.template_set_id`
  - テンプレの世代識別子（tags に `template_set:<id>` を付与）。
  - 同一 `template_set_id` のテンプレのみが選択/更新対象になる。

## テンプレの同一性ルール（固定）
| 観点 | キー | 役割 | 変更タイミング |
| --- | --- | --- | --- |
| 世代 | `run.clearml.template_set_id` | テンプレ世代の主キー | **破壊的変更のみ**（entrypoint/requirements/overrides の大変更） |
| 互換性 | `run.schema_version` | artifacts/manifest の互換キー | 出力スキーマ変更時のみ |
| 実行コード | `run.clearml.code_ref.repository` / `branch` | SCRIPT の repo/branch | ブランチ切替や repo 変更時 |

- template_set は選択の主キー、schema_version は補助キー（詳細は docs/52）。
- schema_version を上げたら templates を再適用し、必要なら template_set を更新する。

## テンプレ定義（YAML）
- 定義ファイル: `conf/clearml/templates.yaml`
- 置換プレースホルダ:
  - `{project_root}` / `{usecase_id}` / `{template_set_id}` / `{schema_version}`
- 変更時は **テンプレ set の切替**とセットで考える。
- tags は `template:true` / `process:<name>` / `template_set:<id>` / `solution:tabular-analysis` を基本とし、
  `usecase:<id>` / `schema:<version>` を併用して選択を安定させる。

## manage_clearml_templates の使い方
推奨: `python -m tabular_analysis.ops.manage_clearml_templates`

```bash
# 設計確認（ClearML不要）
python -m tabular_analysis.ops.manage_clearml_templates --plan --project-root LOCAL

# ClearML 上の候補を一覧表示
python -m tabular_analysis.ops.manage_clearml_templates --list --project-root LOCAL

# テンプレ作成/更新
python -m tabular_analysis.ops.manage_clearml_templates --apply --project-root LOCAL \
  --repo <repo_url> --branch <branch>

# 既存テンプレの妥当性チェック
python -m tabular_analysis.ops.manage_clearml_templates --validate --project-root LOCAL \
  --repo <repo_url> --branch <branch>

# obsolete タグ付与（旧テンプレの整理）
python -m tabular_analysis.ops.manage_clearml_templates --cleanup-obsolete --project-root LOCAL
```

補足:
- `--repo/--branch` は SCRIPT の repository/branch を上書きする。
- `--template-set-id` を指定すると一時的に世代を切り替えられる。
- `--plan` はテンプレ候補の一覧を標準出力で確認する用途。
- commit pin は試験段階では避け、`run.clearml.code_ref.mode=branch` を既定とする（詳細は `docs/69_CLEARML_TROUBLESHOOTING.md`）。

## テンプレ増殖を避ける運用
- **原則**: `template_set_id` は固定し、テンプレ仕様を安定させる。
- 破壊的変更（entrypoint/requirements/overrides の大幅変更）時のみ `template_set_id` を更新する。
- 新世代を作ったら `--cleanup-obsolete` で旧テンプレを `template:deprecated` にする。
- task_id を固定せず、tags で探索する（template_set と process が一致するものを使う）。
- pipeline テンプレは **1 世代 1 つ**に固定し、profile/queue 別の増殖を避ける。

## 変更ポイントまとめ（試験段階）
- `conf/run/base.yaml`: `run.clearml.template_usecase_id` / `run.clearml.template_set_id`
- `conf/run/base.yaml`: `run.schema_version` / `run.clearml.code_ref.*`
- `conf/clearml/templates.yaml`: テンプレの project/entrypoint/overrides/tags
- `src/tabular_analysis/ops/manage_clearml_templates.py`: 選択・validate のロジック
- 仕様変更時は `docs/21_CLEARML_TEMPLATE_TASKS.md` / `docs/41_TEMPLATES_AND_ISSUE_FORMAT.md` に記録
