# T029 分類拡張: 多クラス対応（train/infer/leaderboard/plots）

## Objective
- 既存の classification 対応（T011〜）を **多クラス（3クラス以上）**でも運用できる形に拡張する
- ClearML UI 上で「二値/多クラス」が混ざっても迷わないように、**最小限の properties / artifacts**で表現する
- 追加機能は可能な限り **既存プロセスの拡張（タスク増殖を避ける）**で実現する

---

## Scope（実装範囲）
### 1) config（デフォルト互換）
- `conf/eval/base.yaml` に多クラス用の設定を追加（デフォルトは既存互換）
  - `eval.classification.mode: auto | binary | multiclass`（デフォルト: auto）
  - `eval.classification.top_k: 1`（任意）
  - `eval.metrics.classification_multiclass: [accuracy, f1_macro, logloss]`（例）
  - `eval.primary_metric` の “方向”（maximize/minimize）が classification で正しく扱われるよう整理

### 2) train_model
- 多クラス判定は `y` のユニーク数、または `eval.classification.mode` を優先
- 予測出力
  - `y_pred_label`（argmax）
  - `y_pred_proba`（n_classes 列）
- metrics
  - `accuracy` / `f1_macro` / `log_loss`（最低限）
- 可視化（軽量）
  - confusion matrix を **CSV + PNG**（PNGは小さく）
- 出力（契約）
  - `out.json` に `task_type=classification`, `n_classes`, `class_labels`（必要なら）を含める
  - `manifest.json` 追跡性を壊さない（既存の recipe_hash / split_hash と整合）

### 3) infer
- 多クラス時:
  - `pred_label` と `proba_<class>` を出力（CSV/JSON）
  - `top_k` が指定されていれば top-k も出す（出し方は “追加列” でOK）
- 二値時: 既存互換（proba / label）

### 4) leaderboard
- classification の ranking は maximize（例: f1, accuracy）を基本
- `primary_metric` が maximize か minimize かを `eval` 側で決め、leaderboard はそれに従う
- 多クラスの confusion matrix は train_model 側成果物として扱い、leaderboard は “まとめ” に徹する（Artifacts 増殖抑制）

### 5) tests
- `tools/tests/smoke_multiclass.py` を追加
  - sklearn の `make_classification(n_classes=3)` などで小さなデータを生成
  - preprocess → train_model → infer（最小）
  - 生成物として `confusion_matrix.csv/png` と `out.json(n_classes=3)` を検証

---

## Acceptance Criteria
- 多クラス（3クラス以上）で `train_model` が完走し、`n_classes` が `out.json` に記録される
- 多クラスで `infer` が完走し、確率列が出力される
- confusion matrix が軽量成果物として出る
- `python tools/tests/smoke_multiclass.py` が成功する

---

## Verification（runner が実行）
- `python -m compileall -q src`
- `python tools/tests/smoke_multiclass.py`

---

## Notes / Risks
- 多クラスの校正（calibration）は次タスクで拡張する。ここでは “素の proba” でも良い
- ClearML の “Plots” は増やしすぎない（confusion matrix 1枚程度に留める）

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加/変更した config キー:
- 追加した出力ファイル（Artifacts）:
- verify 結果:
