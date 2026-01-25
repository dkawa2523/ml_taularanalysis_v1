# T024 分類の実務対応: しきい値最適化 +（任意）確率校正

## Objective
- 二値分類で「0.5固定」では業務要件に合わないことが多いので、検証データで **しきい値最適化**できるようにする
- 推論時の出力（label/proba）を安定させ、レポート/比較にも反映する

---

## Scope
1) config 追加（デフォルトは既存互換）
- `conf/eval/base.yaml` に以下を追加
  - `eval.thresholding.enabled: false`（デフォルトは OFF）
  - `eval.thresholding.metric: f1`（例）
  - `eval.thresholding.grid: [0.05,0.10,...,0.95]`（適度な分解能）
  - `eval.calibration.enabled: false`（任意）
  - `eval.calibration.method: sigmoid | isotonic`

2) train_model（classification, binary）
- `eval.thresholding.enabled=true` の場合:
  - 検証データで threshold grid を走査して、metric 最大の threshold を選ぶ
  - `out.json` に `best_threshold` と `threshold_metric` を出力
  - model_bundle に threshold を保存（`postprocess.json` 等）
- それ以外は従来通り（0.5想定）

3) infer（classification）
- model_bundle から threshold を読める場合はそれを使って `pred_label` を出す
- 出力 CSV / JSON に `threshold_used` を記録

4) leaderboard / report への反映
- 推薦モデルの threshold（存在する場合）を report.md に記載

5) テスト追加
- `tools/tests/smoke_thresholding.py`
  - 合成二値データで train_model を thresholding ON で実行
  - `best_threshold` が out.json に存在し、0.0〜1.0 の範囲
  - infer 実行で `threshold_used` が出力される

---

## Implementation Notes
- 二値分類以外（multi-class）はこのタスクでは "明確に非対応" でもよい（error message を明確に）
- threshold 探索は軽量化のため、検証データは必要ならサンプルでOK
- calibration は optional（最初は sigmoid だけでも可）

---

## Acceptance Criteria
- classification（二値）で thresholding が有効化できる
- infer で threshold が使われる
- `smoke_thresholding.py` が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_thresholding.py`
