# T033 分類の確率校正: 二値/多クラスの統一（CalibratedClassifier + reliability plot）

## Objective
- classification の `predict_proba` は過信しやすいので、**確率校正（calibration）**を opt-in で提供する
- 既存の calibration（T024）がある場合は **多クラスを含めて堅牢化**する
- ClearML に大量の曲線を出さず、最小限の可視化（reliability 1枚）に留める

---

## Scope
### 1) config（既存があれば互換拡張）
- `conf/eval/base.yaml` の `eval.calibration.*` を見直し
  - `eval.calibration.enabled: false`
  - `eval.calibration.method: sigmoid | isotonic`
  - `eval.calibration.mode: prefit`（基本は validation で校正）
  - multiclass は one-vs-rest で校正（sklearnの仕様に合わせる）

### 2) train_model（classification）
- base model を学習後、validation を使って校正器を fit
- 校正器（CalibratedClassifierCV など）を model_bundle に保存
- out.json に `calibration.enabled/method/mode` を記録
- 追加 artifacts
  - `calibration_reliability.png`（軽量）
  - `calibration_report.json`（ECE 等は任意。最初は無しでも可）

### 3) infer
- calibration が有効なら **校正後の proba** を出力する（label は argmax or thresholding）
- out.json に “calibrated_proba=true” のような情報を残す

### 4) tests
- `tools/tests/smoke_calibration.py`
  - 二値 or 多クラスの小さな合成データで train_model(calibration enabled) → infer
  - out.json に calibration 情報が入ること
  - reliability.png が生成されること（ファイル存在）

---

## Acceptance Criteria
- 二値・多クラスで calibration が opt-in で動作する
- infer が校正後確率を出す
- `smoke_calibration.py` が通る

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_calibration.py`

---

## Notes / Risks
- isotonic はデータが少ないと過学習しやすいので、デフォルトは sigmoid 推奨
- plot は 1枚に抑え、ClearML の “Plots” タブが散らからないようにする

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加/変更した config キー:
- verify 結果:
