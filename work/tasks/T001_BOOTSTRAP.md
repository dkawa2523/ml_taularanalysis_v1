# T001 Bootstrap: パッケージ化/CLI/基本導線

## Objective
- Solution Repo として最低限の「動く器」を完成させる
- Codex ループ（tools/codex_loop/run.py）が `work/queue.json` / `work/state.json` を読み、次タスクを実行できる状態にする

## Context
- plan2.md に従い、Platform と Solution は分離する（platform は別 repo / 別インストール）
- 本タスクでは「実 ML ロジック」は実装しない（T004 以降）

## Files to touch (must)
- `tools/codex_loop/run.py`
- （必要なら）`pyproject.toml`, `src/tabular_analysis/cli.py`
- `work/state.json`（run.py が更新する）

## Instructions
1. `tools/codex_loop/run.py` を実装する
   - `work/queue.json` からタスクを読み取る
   - `work/state.json` で status を管理する（todo / in_progress / done / failed）
   - `--once` で 1 タスクのみ、未指定で連続実行
   - `runtime.json` の `cmd/args` に従って codex CLI を起動する（{prompt_file} を置換）
   - codex 実行後に verify を実行し、成功したら state を done にする
   - 失敗時はログを `work/runs/<timestamp>_<taskid>/` に保存し、state を failed にする

2. prompt 生成ポリシー
   - `work/CODEX_GUIDE.md` + 対象タスク markdown（T001 以外）を結合して prompt にする
   - `docs/` は参照パスだけ提示し、全文貼り付けは最小限（長文化で迷走するため）
   - 直前の失敗ログ（あれば）を次 prompt に注入する

3. must_change_globs のチェック
   - queue.json の `must_change_globs` に合致するファイルが 1つ以上変更されたことを確認する
   - 変更判定は git があれば git diff、無ければハッシュ差分でよい

## Acceptance Criteria
- `python -m tabular_analysis.cli --print-config` が repo root で動く
- `python tools/codex_loop/run.py --repo . --dry-run` が「次に実行するタスク」を表示できる
- state.json が更新される

## Verification
```bash
python -m compileall -q src
python -m tabular_analysis.cli --print-config > /dev/null
python tools/codex_loop/run.py --repo . --dry-run
```
