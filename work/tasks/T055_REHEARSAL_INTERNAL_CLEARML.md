# T055 試験段階: 社内ClearMLへ移行する差分チェックと微調整手順を整備

## Objective

ローカルClearMLでの試験が終わったら、社内ClearMLへ接続先を切り替えて同じリハーサルを行う。
この移行でつまずきやすい点（ストレージ、Agent環境差、権限、ネットワーク）を **事前にチェックリスト化**し、
調整ポイントを docs とツールで残す。

## Constraints

- 試験段階ではClearML運用ルール（queue、権限、retention）を固定しない
- コード側からQueue名を強制しない（UI側の操作を前提）

## Implementation Outline

1) `tools/rehearsal/plan_migration.py` を追加
   - `--from local --to internal` のように指定すると
     「差分チェックリスト」「切替手順」「よくあるエラー」を表示
   - 実際のサーバー疎通テストはユーザーが行う（このスクリプトは“ガイド”）

2) docs を追加/更新
   - `docs/42_REHEARSAL_SCENARIOS.md` に社内移行の章を増やす
   - `docs/issues/DECISIONS.md` に “社内移行時の決定事項” の枠を作る

## Acceptance Criteria

- `plan_migration.py --help` が表示される
- ローカル→社内の移行で、最低限チェックすべき項目が docs にまとまっている

## Verification

```bash
python tools/rehearsal/plan_migration.py --help
```

## RESULT

<!-- Codex fills -->
