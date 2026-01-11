# Codex loop hotfix v4

このパッチは `tools/codex_loop/run.py` を更新し、次の2点で **自動実行が止まりにくい** ようにします。

1. `must_change_globs` が変更無しでも **失敗にしない**（警告にして verify を継続）
   - 既に実装済み/同内容が反映済みの「冪等タスク」で止まる問題を防ぎます。

2. 失敗済みタスクを再実行する際、まず **verify を先に実行**して、既に満たしていれば Codex を起動せずに DONE にします
   - 余計な Codex 実行（トークン消費）と繰り返し失敗を減らします。
   - 無効化したい場合は `--no-preverify-failed` を付けます。

## 適用方法

`ml-solution-tabular-analysis` がある workspace 直下で unzip してください。

```bash
cd <workspace>
unzip -o ml_solution_tabular_analysis_codeloop_hotfix_v4.zip -d .
```

## 再実行

```bash
cd <workspace>/ml-solution-tabular-analysis
python tools/codex_loop/run.py --repo . --once
```

必要なら preverify を無効化：

```bash
python tools/codex_loop/run.py --repo . --once --no-preverify-failed
```
