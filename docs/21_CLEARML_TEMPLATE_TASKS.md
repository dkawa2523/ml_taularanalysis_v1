# 21_CLEARML_TEMPLATE_TASKS（Clone 運用の標準化）

## Purpose
ClearML UI から「Clone して実行」する運用を安定させるために、
**template task の project / entrypoint / overrides を固定化**します。

- Clone 後にユーザーが触るのは **override のみ**
- project / task 名 / entrypoint はテンプレの定義に従って固定
- 運用ルールの単一の正は `docs/81_CLEARML_TEMPLATE_POLICY.md`

## Spec（テンプレ定義）
- Spec: `conf/clearml/templates.yaml`
- Lock: `conf/clearml/templates.lock.yaml`（apply 時に作成）

テンプレには以下を定義します:
- `project_name`
- `task_name_template`
- `entrypoint`
- `default_overrides`
- `tags`
- `properties_minimal`
- `requirements`（ClearML Agent が最小依存を入れるための一覧）

## 事前チェック（必須）
- `uv.lock` がリポジトリ直下にあること（`uv lock` で更新）
- ClearML の接続情報（`clearml.conf` または `CLEARML_*` 環境変数）
- Agent からリポジトリを clone できること（private repo は認証必須）

## Plan / Apply / Validate
ClearML を使えない環境でも **plan は必ず生成**できます。

### Plan（ClearML 不要）
```bash
python -m tabular_analysis.ops.manage_clearml_templates --plan
```
- 出力: 標準出力（plan はファイルに保存しない）

### Apply（ClearML 必須）
```bash
python -m tabular_analysis.ops.manage_clearml_templates --apply
```
- 既存テンプレがあれば `conf/clearml/templates.lock.yaml` の task_id を再利用
- 作成した task_id は lock に保存
- requirements / entrypoint / tags が現行の spec に合うよう自動更新

### Validate（ClearML 必須）
```bash
python -m tabular_analysis.ops.manage_clearml_templates --validate
```
- lock に保存された task_id の存在を確認
- repository / branch / entrypoint の一致を確認

## ClearML Agent 実行の前提
- テンプレは `run.clearml.env.bootstrap=uv` を既定にしており、
  実行時に `uv sync --all-extras --frozen` で `.venv` を構築して再実行する。
- templates は `run.clearml.env.uv.all_extras=true` を既定にする。
- `infer.mode=optimize` の optuna も all-extras に含まれる。

## Template 一覧（現行）
- dataset_register
- preprocess
- train_model
- train_ensemble
- infer
- leaderboard
- pipeline
- promote_model

## Run Rule（Clone 実行時）
- 変更するのは override のみ
- tags / properties は UI 契約に沿って自動付与される想定
- queue / entrypoint はテンプレ側で固定

## 運用ルール（事故防止）
- テンプレ更新後は Queue 内の旧タスクを UI で削除し、再 clone する
- `run.clearml.code_ref.mode=branch` を試験段階の既定とする
