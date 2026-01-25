# ClearML の PIPELINES タブに表示させるための要点 v1

## 目的
- train pipeline を ClearML UI の左タブ「PIPELINES」に表示し、子タスク階層と依存関係を追えるようにする。

## 重要ポイント（実装側）
- controller task が `TaskTypes.controller` かつ system tag `pipeline` を持つこと（PIPELINES タブに出る条件）
- `run.clearml.execution=pipeline_controller` のときは `controller.start(queue=...)` を使い controller 自体を agent 実行
- ローカルデバッグ用に `run.clearml.execution=pipeline_controller_local` を用意し、`start_locally` で実行
- project を pipeline 専用（例: `.../99_pipeline`）に統一し、探索しやすくする（configで変更可能）
- template task の tags が揃っており、clone 元が見つかること（詳細は `docs/81_CLEARML_TEMPLATE_POLICY.md`）
  - tags: `template:true`, `process:<name>`, `template_set:<id>`, `solution:tabular-analysis`
  - `usecase:<id>` / `schema:<version>` があれば優先して一致させる
  - 見つからない場合は `python -m tabular_analysis.ops.manage_clearml_templates --apply` の案内を出す
- template clone を前提に local/logging と UI の見え方を揃える（commit pin 注意は `docs/69_CLEARML_TROUBLESHOOTING.md`）

## 検証手順（運用）
1) template を作成/validate（manage_clearml_templates）
2) agent を起動（queue名を合わせる）
3) `run.clearml.execution=pipeline_controller` で pipeline を実行
4) ClearML UI: PIPELINES タブに pipeline が出るか確認
5) ローカルデバッグは `run.clearml.execution=pipeline_controller_local` を使用
