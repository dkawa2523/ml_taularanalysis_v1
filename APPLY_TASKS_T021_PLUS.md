# APPLY_TASKS_T021_PLUS.md

このZIPは **ml-solution-tabular-analysis** リポジトリに、T021〜T028 の Codex CLI タスク定義を「追加」するための差分パッケージです。

- 既存の実装（T001〜T020）を維持したまま、次フェーズ（運用投入・品質強化）へ進むためのタスクを追加します。
- `work/state.json`（進捗）は上書きしない想定です。

---

## 1) 展開場所（重要）
展開先は **リポジトリ直下ではなく、リポジトリの親ディレクトリ** を推奨します。

例：
```
workspace/
  ml-solution-tabular-analysis/   # 既存 repo
```

この状態で `workspace` に移動して unzip します。

```bash
cd <workspace>
unzip -o ml_solution_tabular_analysis_codex_tasks_T021_T028_v1.zip -d .
```

> 間違って `ml-solution-tabular-analysis/ml-solution-tabular-analysis/...` の二重ディレクトリができた場合は、内側の `ml-solution-tabular-analysis/` を外側へマージしてネストを解消してください。

---

## 2) 反映確認
```bash
cd <workspace>/ml-solution-tabular-analysis
ls -la work/tasks | grep T021
jq '.tasks[-1].id' work/queue.json
```

---

## 3) Codex loop 実行（次タスクから）
```bash
python tools/codex_loop/run.py --repo . --status
python tools/codex_loop/run.py --repo . --once
```

連続実行する場合：
```bash
python tools/codex_loop/run.py --repo .
```

---

## 4) よくあるトラブル
- `in_progress` のまま止まる：
  ```bash
  python tools/codex_loop/run.py --repo . --reset-in-progress
  ```
- ロックが残って動かない：
  ```bash
  python tools/codex_loop/run.py --repo . --force-lock --once
  ```
