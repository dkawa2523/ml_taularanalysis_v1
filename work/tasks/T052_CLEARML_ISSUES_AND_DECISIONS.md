# T052 試験段階: ClearML運用検討をIssue(md)として残す枠組みを追加

## Objective

試験段階では運用ルールを固定しない。その代わり、
「何を試し、何が良く/悪く、どれを採用するか」を**必ず文書化**する。

このタスクでは、docs配下に “意思決定ログ” と “Issueテンプレ” を追加する。

## Scope

- `docs/issues/README.md`：Issue運用のルール（1ファイル）
- `docs/issues/ISSUE_TEMPLATE.md`：テンプレ（`docs/41_...` のテンプレと整合）
- `docs/issues/DECISIONS.md`：決定ログ（いつ/何/なぜ）
- 初期Issueをいくつか作る（未決のままOK）

## Constraints

- 本番の運用ルールを押し付けない（候補を複数残す）
- ClearMLサーバー設定（権限/queue/retention）はここでは変えない

## Acceptance Criteria

- `docs/issues/README.md` があり、Issueの書き方が統一されている
- `docs/issues/DECISIONS.md` に、少なくとも以下の項目が “未決” として並ぶ
  - project階層（案A/B/C）
  - usecase_id規約（試験→本番）
  - tags/properties最小セット
  - template task運用案
  - model registryのstage運用

## Verification

```bash
python -c "import pathlib; assert (pathlib.Path('docs/issues')/ 'README.md').exists()"
python -c "import pathlib; assert (pathlib.Path('docs/issues')/ 'DECISIONS.md').exists()"
```

## RESULT

<!-- Codex fills -->
