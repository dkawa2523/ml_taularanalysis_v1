# T032 回帰の不確かさ: Conformal prediction（split conformal の予測区間）

## Objective
- 業務では「予測値」だけでなく「不確かさ（予測区間）」が重要なため、回帰に **予測区間**を追加する
- 依存追加を避け、**split conformal**（validation 残差の分位点）でまず提供する
- デフォルトOFF（opt-in）で ClearML のノイズを増やさない

---

## Scope
### 1) config（デフォルトOFF）
- `conf/eval/base.yaml` に追加
  - `eval.uncertainty.enabled: false`
  - `eval.uncertainty.method: conformal_split`
  - `eval.uncertainty.alpha: 0.1`（90% interval）
  - `eval.uncertainty.use_abs_residual: true`

### 2) train_model（回帰のみ）
- validation の residual を使って `q = quantile(|y - y_pred|, 1-alpha)` を計算
- `model_bundle`（または同等の保存物）に `q` と計算条件を保存
- out.json / metrics.json に `uncertainty` セクションを追加（enabled/method/alpha/q）

### 3) infer（回帰のみ）
- `pred` に加えて
  - `pred_lower = pred - q`
  - `pred_upper = pred + q`
- 追加列は最小限（3列）にする
- 出力 `summary.md` に区間の意味（alpha）を明記

### 4) 可視化（軽量）
- interval width の簡易ヒストグラム（png 1枚程度、opt-in）

### 5) tests
- `tools/tests/smoke_uncertainty.py`
  - 小さな合成回帰データで train → infer を実行し
  - infer 出力に lower/upper が含まれること
  - out.json に uncertainty.q が記録されること

---

## Acceptance Criteria
- 不確かさ推定を opt-in で有効化できる
- infer 出力に lower/upper が含まれる
- `smoke_uncertainty.py` が通る

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_uncertainty.py`

---

## Notes / Risks
- 本方式は “分布に依存しない” が、coverage の厳密検証はデータ依存で揺れるため smoke では列存在と q 記録を検証する
- classification の不確かさ（entropy等）は別途検討（今回は回帰に限定）

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加/変更した config キー:
- verify 結果:
