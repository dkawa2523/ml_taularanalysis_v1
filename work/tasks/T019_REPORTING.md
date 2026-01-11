# T019 レポート: pipeline 実行の summary/report.md を自動生成（ClearMLで見やすく）

## Objective
- 非DSユーザーが ClearML UI で迷わないよう、pipeline 実行の “結論” を 1枚のレポートにまとめる
- 既存の artifacts（leaderboard.csv / recommendation.json / metrics.json 等）を参照して **サマリーを自動生成**する

---

## Scope
1) `src/tabular_analysis/reporting/report.py` を追加
   - `build_pipeline_report(pipeline_run_json, ...) -> Markdown str` 等
2) pipeline の最後で `report.md`（または `summary.md`）を生成し artifacts に含める
   - 目次例:
     - データ概要（行数/列数/target）
     - split/recipe/hash
     - 試したモデル一覧（上位N）
     - 推薦モデル（metric + score + model_id）
     - 次アクション（例: HPOを増やす、特定特徴量の確認）
3) ClearML enabled 時は、Artifacts としてアップロード（UI 上で即見える形）
4) テスト追加: `tools/tests/smoke_report.py`
   - pipeline を（HPOなしでもよい）1回実行し、report.md が生成されることを検証

---

## Acceptance Criteria
- pipeline 出力に report.md が追加される
- report.md が “結論ファースト” で読みやすい
- smoke_report.py が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_report.py`
