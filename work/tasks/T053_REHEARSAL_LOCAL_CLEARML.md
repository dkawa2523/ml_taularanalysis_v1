# T053 試験段階: ローカルClearML用リハーサル手順とスクリプトを整備

## Objective

ローカルClearML（開発PC上の試験サーバー）で、T050までの機能を **毎回同じ手順で再現**できるようにする。

このタスクでは「人間が読む手順（docs）」と「自動で回すスクリプト（tools）」を用意し、
試験で得られた結果を後で比較しやすくする。

## Constraints

- ClearMLサーバー/Queue設定をコードから強制しない
- ClearMLが無い環境でも `--dry-run` で手順確認できるようにする

## Implementation Outline

1) `tools/rehearsal/run_rehearsal.py` を追加
   - `--mode local`（ClearML無効）
   - `--mode logging`（ClearML有効・ローカル実行）
   - `--dry-run`（コマンドを表示するだけ）
   - 内部では既存CLI/スモークを呼び出す（新規の重い依存は入れない）

2) `docs/42_REHEARSAL_SCENARIOS.md` の内容をスクリプトに整合させる

3) 実行後に残すもの
   - `work/rehearsal/` 配下に `rehearsal_log.md`（実行環境・usecase_id・結果）
   - 成果物は既存の `report.md` / `decision_summary.md` を参照

## Acceptance Criteria

- `python tools/rehearsal/run_rehearsal.py --help` が表示される
- `--dry-run` で実行したとき、実際に叩く予定のコマンド一覧が表示される
- 既存の smoke を壊さない

## Verification

```bash
python tools/rehearsal/run_rehearsal.py --help
python tools/rehearsal/run_rehearsal.py --mode local --dry-run
```

## RESULT

<!-- Codex fills -->
