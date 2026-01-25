# T030 分類の実務対応: 不均衡データ（class_weight / PR-AUC / 運用ノイズ抑制）

## Objective
- 不均衡（二値/多クラス）で “accuracy が高いだけ” にならないように、**不均衡対応を opt-in で提供**する
- 依存追加を最小にし、基本は **scikit-learnのみ**で動く（外部 resampling は optional）
- ClearML 上の比較（leaderboard）でノイズが増えないよう、必要最小限の情報だけを追加する

---

## Scope
### 1) config（デフォルトOFF）
- `conf/eval/base.yaml` に追加
  - `eval.imbalance.enabled: false`
  - `eval.imbalance.strategy: class_weight | pos_weight | (optional) oversample | undersample`
  - `eval.imbalance.class_weight: balanced | null`
  - `eval.metrics.classification_imbalance: [pr_auc, balanced_accuracy, fbeta]`（例）
- 既存の thresholding（T024）と併用できるようにする
  - PR-AUC を primary_metric にした場合も leaderboard が正しく maximize できること

### 2) train_model
- sklearn 系:
  - `class_weight` を受け取れるモデルにのみ適用（受け取れない場合は警告 + 無視）
- GBDT 系（lightgbm/xgboost/catboost）:
  - optional dependency がある場合のみ適用
  - 無い場合は “スキップした” ことを out.json に明示（落とさない）
- metrics:
  - `pr_auc`（二値のみ）
  - `balanced_accuracy`
  - `fbeta`（beta は config で指定）
- 出力:
  - out.json に `imbalance.enabled/strategy` と “適用可否” を記録（ClearML properties も同様）

### 3) tests
- `tools/tests/smoke_imbalance.py`
  - 不均衡データ（例えば positive 5%）を生成
  - `eval.imbalance.enabled=true` で train_model が完走
  - `balanced_accuracy` 等が metrics に入ることを検証

---

## Acceptance Criteria
- 不均衡設定を ON にしても、各モデルで “落ちずに” 動く（適用できないモデルは明示してスキップ）
- `smoke_imbalance.py` が通る
- ClearML 上でタスクが増殖しない（既存 task を拡張するだけ）

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_imbalance.py`

---

## Notes / Risks
- oversample/undersample は `imblearn` を入れると簡単だが依存が増えるため **optional** にする
- pr_auc は多クラスだと扱いが複雑になるため、初期は二値のみ（多クラスは macro 版を後続で検討）

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加/変更した config キー:
- verify 結果:
