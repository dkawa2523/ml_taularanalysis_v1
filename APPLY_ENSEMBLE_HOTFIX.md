# APPLY: Ensemble tasks HOTFIX (T083〜T086)

このZIPは **未実行のアンサンブル関連タスク（T083〜T086）の指示ファイルだけ**を差し替えるためのものです。
T077 を実行中でも、T083 に到達する前であれば安全に適用できます。

## 変更の要点
- 失敗/重いモデル（TabPFN/GaussianProcess/SVR/SVC/外部依存など）が混ざっても、
  ensemble タスクが全体を落とさず **スキップ**して進む
- 分類では `predict_proba` と `classes` の整合を必須化（揃わない候補は除外）
- stacking はリークしにくい評価手順を必須化し、`primary_metric_source` を明記
- leaderboard は single/ensemble を同列表示しつつ、recommend は metric_source 混在で暴走しない

## 適用手順（上書き）
1) リポジトリ直下で ZIP を展開して上書きコピー

```bash
cd /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
# 例: ダウンロードしたzipを任意の場所に置いてから
unzip -o /path/to/ml_solution_tabular_analysis_ensemble_hotfix_v1.zip -d .
```

2) queue.json の編集は不要
- `work/queue.json` は既に T083〜T086 を参照しているため、**mdの差し替えだけで反映されます**。

3) Codex loop を続行
```bash
python tools/codex_loop/run.py --repo . --status
python tools/codex_loop/run.py --repo .
```

## 注意
- すでに T083〜T086 を実行済みの場合、mdを差し替えても過去実行結果は変わりません。
  その場合は、該当タスクを `todo` に戻して再実行するか、別IDで追タスク化してください。
