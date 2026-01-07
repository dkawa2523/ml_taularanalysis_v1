# ClearML運用の決定ログ（試験段階）

試験段階では運用ルールを固定しません。
ここには「候補の比較」と「最終決定（いつ/誰が/なぜ）」のみを記録します。

## 1. project階層（案A/B/C）: 未決

- 関連Issue: `docs/issues/ISSUE_PROJECT_HIERARCHY.md`
- 案A: `<project_root>/<usecase_id>/<process>`
- 案B: `<project_root>/<usecase_id>/<run_group>/<process>`
- 案C: `<project_root>/experiments/<usecase_id>/<process>`
- 判定観点: UIの見やすさ、検索性、テンプレTask配置の自然さ
- 決定ログ: 未決

## 2. usecase_id規約（試験→本番）: 未決

- 関連Issue: `docs/issues/ISSUE_USECASE_ID_POLICY.md`
- 案A: `uc_<domain>_<problem>_<v1>`
- 案B: `uc_<domain>_<problem>` + project_root で環境分離
- 案C: `uc_<domain>_<problem>__<env>`（test/prodなど）
- 判定観点: 人が読める、UIのソート性、移行コスト
- 決定ログ: 未決

## 3. tags/properties最小セット: 未決

- 関連Issue: `docs/issues/ISSUE_TAGS_PROPERTIES_MIN_SET.md`
- 案A: tags=[usecase_id, process], properties={usecase_id, dataset_id, model_id}
- 案B: tags=[usecase_id, phase], properties={usecase_id, run_id}
- 案C: tags=[], properties={usecase_id}（詳細はartifactに寄せる）
- 判定観点: 検索性、ノイズ量、UI契約の維持
- 決定ログ: 未決

## 4. template task運用案: 未決

- 関連Issue: `docs/issues/ISSUE_TEMPLATE_TASK_OPERATION.md`
- 案A: UIでの手動clone運用を継続
- 案B: 小さなCLIでclone+queueを補助（将来）
- 案C: pipeline cloneでパラメータを注入
- 判定観点: 事故率、再現性、権限制約
- 決定ログ: 未決

## 5. model registryのstage運用: 未決

- 関連Issue: `docs/issues/ISSUE_MODEL_REGISTRY_STAGE.md`
- 案A: candidate -> staging -> prod
- 案B: challenger/champion
- 案C: dev/prod の2段階
- 判定観点: promote/rollbackの運用負荷、UIでの理解しやすさ
- 決定ログ: 未決

## 6. 社内ClearML移行時の決定事項: 未決

- 関連Issue: 未作成（必要になったら `docs/issues/ISSUE_INTERNAL_CLEARML_MIGRATION.md` を作成）
- 対象: artifacts保存先、agent実行環境、認証/権限、network/proxy、retention
- 判定観点: セキュリティ、運用負荷、コスト、UI契約の維持
- 決定ログ: 未決
