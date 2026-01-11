# T059 Template Task 作成/更新ツール整備（試験段階: local serverで簡単に作れる）

## Objective
pipeline_controller が参照する template task をローカルClearML上で作成・更新できるCLIを追加し、docsで手順を明文化する。

## Risk / Redundancy check (read before coding)
- 変更は **ClearML統合の薄い層**（`src/tabular_analysis/clearml/`）へ集約し、process側に重複ロジックを散らさない。
- HyperParameters/Configuration は **最小**。全文connect禁止（UIがノイズで死ぬ）。
- local pipeline と pipeline_controller の仕様二重化を避ける（plan/step定義を共通化）。

## Context / Why
controller方式は template task が必須。試験段階では運用固定はしないが、templateが作れないとcontroller検証ができない。

## Instructions (do exactly)
1. `src/tabular_analysis/ops/manage_clearml_templates.py` を実装（single entrypoint）:
   - `--plan` : 作成すべき template 一覧を表示（process別、project_rootは引数）
   - `--apply` : template を作成（存在すれば“変更最小”で更新 or スキップ）
   - `--validate` : template の存在と tags/script を検証
2. template 付与タグ（必須）:
   - `template:true`
   - `process:<dataset_register|preprocess|train_model|leaderboard|infer|pipeline>`
   - `solution:tabular-analysis`（任意だが推奨）
3. template の script:
   - agent が実行できるよう `Task.set_script` で repo/branch/entrypoint を正しく設定
   - repo/branch は「実行者が後で変更できる」ように config/引数で指定（固定しない）
4. template 探索は tags ベースのまま（試験段階）。task_id固定はしない。
5. docs:
   - docs/41, docs/42 を更新し、ローカルClearMLで template を作る手順を追加


## Acceptance Criteria
- `--plan` で必要テンプレ一覧が出る。
- `--apply` でローカルClearMLにテンプレが作成され、`--validate` が通る。
- pipeline_controller がテンプレ探索でテンプレを見つけられる。


## Verification (run locally)
```bash
python -m compileall -q src
python -m tabular_analysis.ops.manage_clearml_templates --help
# ローカルClearMLが起動している場合:
# python -m tabular_analysis.ops.manage_clearml_templates --apply --project-root LOCAL
# python -m tabular_analysis.ops.manage_clearml_templates --validate --project-root LOCAL

```

## Result
- RESULT: TODO (nonce: <fill>)
