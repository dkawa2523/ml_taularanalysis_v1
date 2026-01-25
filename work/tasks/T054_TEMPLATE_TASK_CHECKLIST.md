# T054 試験段階: Template Task(将来)の作成・チェック手順をdocsに明文化

## Objective

試験段階では、テンプレTask運用を **強制しない**。
ただし将来の運用で「UIからCloneして実行」が基本になるため、作り方・チェック項目を docs に明文化し、
後から把握・改良しやすくする。

## Scope

- `docs/41_TEMPLATES_AND_ISSUE_FORMAT.md` を補強（チェックリストを増やす）
- `docs/issues/` にテンプレ運用の検討Issueを1つ追加（未決でOK）

## Acceptance Criteria

- テンプレTaskの作り方が「手順」「確認ポイント」「よくある失敗」で整理されている
- 試験段階での前提（コードがqueueを強制しない等）が明記されている

## Verification

```bash
python -c "import pathlib; assert (pathlib.Path('docs')/ '41_TEMPLATES_AND_ISSUE_FORMAT.md').exists()"
```

## RESULT

<!-- Codex fills -->
