# ml-solution-tabular-analysis: Codex tasks add-on (T089〜T097)

このパッケージは **コード本体ではなく、Codex CLI に自動実装させるための指示（work/tasks/*.md）** を提供します。

## 含まれるもの
- `work/tasks/T089_...md` 〜 `T097_...md`
- `work/queue_additions_T089_T097_v1.json`（work/queue.json に追記するための差分）
- `APPLY_T089_T097.md`（適用手順）

## ねらい（今回の改良テーマ）
- pipeline の “設定爆発” を防ぎつつ拡張できる設計（profile / groups.mode / base+差分）
- preprocess を複数variantで同一階層実行し、train を展開できる plan builder
- optional deps / inapplicable を落とさず SKIP として正規化
- partial failure（fail_policy）と run_summary による運用固定
- limits / parallelism / dry-run による事故防止
- Local/Agent 実行で ClearML 上の見え方を揃える（plan + driver）
- Python rehearsal runner による自動検証（jq不要）
- docs の運用ルール/拡張点をレビューしやすく整理
