# T027 監視の第一歩: drift_report（train vs infer の分布差）

## Objective
- 本番運用では、データ分布の変化（ドリフト）を把握しないとモデル性能が静かに劣化する
- 学習時に特徴量分布の "プロフィール" を保存し、推論時に簡易ドリフト指標（PSI 等）を出力する

---

## Scope
1) train 時に profile を保存
- `train_model` で学習データ（train split）の特徴量分布サマリを計算し、model_bundle に `train_profile.json` を保存
- 数値: mean/std/quantiles/簡易ヒストグラム（bin edges + counts）
- カテゴリ: 上位カテゴリ頻度 + other

2) infer 時に drift を計算
- 入力データの profile と train_profile を比較し、以下を出力
  - 数値: PSI（bin ベース）
  - カテゴリ: PSI（頻度ベース）
- 出力: `drift_report.json`（必須） + `drift_report.md`（推奨）
- `out.json` に `drift_report_path` を追加

3) config
- `infer.drift.enabled: false`（デフォルトOFF）
- `infer.drift.psi_warn_threshold: 0.2`（例）
- `infer.drift.psi_fail_threshold: 0.4`（例、strict のときのみ使用）

4) テスト追加
- `tools/tests/smoke_drift_report.py`
  - 学習データと、分布を意図的にずらした推論データで infer を実行し、drift_report.json が出ること

---

## Acceptance Criteria
- drift_report.json を生成できる
- `infer.drift.enabled=true` の時だけ動く（既存互換）
- smoke_drift_report.py が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_drift_report.py`
