# T034 評価の堅牢化: 指標の信頼区間（bootstrap CI）

## Objective
- モデル間の差が僅差の場合に “たまたま” かどうか判断できるよう、評価指標に **信頼区間（CI）**を付与する
- 比較（leaderboard）の運用に支障が出ないよう、**点推定は従来通り**、CI は補助情報として追加する
- 計算負荷を抑える（デフォルトOFF / small n_boot）

---

## Scope
### 1) config（デフォルトOFF）
- `conf/eval/base.yaml` に追加
  - `eval.ci.enabled: false`
  - `eval.ci.n_boot: 200`（smoke で耐える値）
  - `eval.ci.alpha: 0.05`（95% CI）
  - `eval.ci.seed: 0`

### 2) train_model
- validation の `y_true` と `y_pred`（必要なら proba）から bootstrap resampling で primary_metric の分布を計算
- `metrics_ci.json` を出力（例）
  - `{ "primary_metric": {"low":..., "mid":..., "high":...}, "n_boot":..., "alpha":... }`
- out.json に CI を要約して記録（leaderboard が拾えるように）

### 3) leaderboard
- leaderboard.csv に CI 列を追加（例: `primary_metric_ci_low`, `..._high`）
- 推奨モデルの decision summary に CI を含める（文字数は増やしすぎない）

### 4) tests
- `tools/tests/smoke_metric_ci.py`
  - CI enabled で train_model を回し `metrics_ci.json` が出ること
  - leaderboard が CI 列を読み込めること（最小）

---

## Acceptance Criteria
- CI を opt-in で生成できる
- leaderboard に CI が反映される
- `smoke_metric_ci.py` が通る

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_metric_ci.py`

---

## Notes / Risks
- bootstrap は重いので n_boot は小さめから。full運用では増やせるようにする
- classification の AUC 等は例外処理が必要（クラス欠落など）→ resample 時に安全にスキップ/再試行する

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加/変更した config キー:
- verify 結果:
