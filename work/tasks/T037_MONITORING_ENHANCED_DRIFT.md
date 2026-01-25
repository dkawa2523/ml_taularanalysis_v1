# T037 監視強化: train profile ↔ infer profile による drift 詳細化（opt-in）

## Objective
- T027 の drift_report を “運用で使える” 形に強化する
  - train 時に profile（分布要約）を保存
  - infer 時に入力データの profile を計算し、train との差分を drift として記録
- 計算コストと ClearML ノイズを抑える（デフォルトOFF / サンプルでOK）

---

## Scope
### 1) config（デフォルトOFF）
- `conf/run/base.yaml` もしくは `conf/monitor/base.yaml` に追加（既存設計に合わせる）
  - `monitor.drift.enabled: false`
  - `monitor.drift.sample_n: 5000`（大きい場合はサンプル）
  - `monitor.drift.metrics: [psi, ks]`（psiはカテゴリにも対応、ksは数値のみ）
  - `monitor.drift.alert_thresholds.psi: 0.2`（例）

### 2) train_model
- 学習データ（または validation）から “baseline profile” を保存
  - 数値: mean/std/quantiles
  - カテゴリ: top-k の頻度（kは小さく）
- `train_profile.json` として model_bundle に含める（または artifacts）

### 3) infer
- 入力データの profile を計算（サンプルでOK）
- train_profile と比較して drift 指標（PSI 等）を計算
- `drift_report.json` を出力し、上位 drift feature を summary.md に記載
- alert 判定（threshold 超え）なら `out.json` に `drift_alert=true` を記録（properties へも反映）

### 4) tests
- `tools/tests/smoke_drift_enhanced.py`
  - train → infer で train_profile.json が使われる
  - drift_report.json が生成される
  - フォーマットが期待通り

---

## Acceptance Criteria
- drift 詳細化が opt-in で動く
- train_profile / drift_report が生成される
- `smoke_drift_enhanced.py` が通る

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_drift_enhanced.py`

---

## Notes / Risks
- “全列の完全ヒストグラム” は重いので避ける（要約統計 + top-k）
- PSI 実装はカテゴリでのbin設計に注意（安定な方法で）

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加/変更した config キー:
- verify 結果:
