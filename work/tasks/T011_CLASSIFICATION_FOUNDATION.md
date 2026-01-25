# T011 分類対応: eval.task_type + 分類メトリクス + infer/leaderboard 対応

## Objective
- 既存の回帰パイプライン（preprocess/train/leaderboard/infer）を壊さずに、**分類（classification）** を扱えるようにする
- ClearML UI 契約（docs/03）と追跡性（manifest + properties）を維持したまま、**分類でも比較・推薦できる**状態にする

## 背景（なぜ必要か）
- 業務投入を前提にすると、テーブルデータは回帰だけでなく分類（例: 合否判定、異常判定、カテゴリ予測）が頻出
- 現状は回帰（rmse 等）を主軸にしているため、分類へ拡張して「基盤」として使えるようにする

---

## Scope（このタスクでやること）
1) config に `eval.task_type` を追加（`regression | classification`）
2) metrics を分類対応（accuracy / f1 / roc_auc / log_loss など）
3) train_model を分類対応（y の前処理、predict/predict_proba の扱い、metrics 出力）
4) infer を分類対応（ラベル + 確率の出力設計）
5) leaderboard の比較可能性に task_type を追加（混在させない）
6) 最低限の分類モデルとして `LogisticRegression` を追加（conf/group/model）
7) **ローカル smoke** を追加して verify を強化（中途半端完了防止）

---

## Implementation Notes（重要）
### A. 互換性（最重要）
- 回帰の動作（T010 まで）を壊さないこと
- `eval.task_type` のデフォルトは **regression** にする（既存ワークフローを変更しない）

### B. metrics 設計
- `registry/metrics.py` に、次を満たす関数群を用意
  - `get_metric(name, task_type, **kwargs) -> callable`
  - `metric_direction(name, task_type) -> "minimize" | "maximize"`
  - `metric_requires_proba(name, task_type) -> bool`（roc_auc / log_loss など）
- 分類の roc_auc は binary をまず確実に対応（multi-class は将来拡張、ただし落ち方は明確に）

### C. train_model（分類）
- `eval.task_type=classification` の場合:
  - y を `LabelEncoder` 等で整数化（必要なら）し、**encoder を model_bundle に含める**
  - primary_metric の計算で `predict_proba` が必要なら確率を使う
  - out.json/manifest/properties に `task_type` と `n_classes` を記録
- “勝手に別の metric に切り替える” は禁止（再現性が壊れる）

### D. infer（分類）
- single: `predicted_label` と `predicted_proba`（辞書 or 配列）を out.json に含めるか、predictions.json を出す
- batch: 出力 CSV に
  - `pred_label`
  - `pred_proba_<class>`（二値なら `pred_proba_1` など）
  を追加する（少なくともラベルは必須）

### E. leaderboard（分類）
- 比較可能性（comparable）判定に **task_type** を追加（回帰と分類を混ぜない）
- direction を必ず参照して順位を決める

### F. モデル追加（最小）
- `conf/group/model/logistic_regression.yaml` を追加
  - `sklearn.linear_model.LogisticRegression`
  - `max_iter` を入れて収束で止まらないように
  - `random_state` を seed に合わせる（solver によっては無視されるが害はない）

---

## Acceptance Criteria
- `eval.task_type=classification` で `train_model` が完走する
- `infer` が分類の出力（ラベル/確率）を生成する
- `leaderboard` が分類モデル同士を比較し、推薦モデルを出せる
- **smoke_classification.py が通る**（ClearML disabled, ローカルのみ）

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_classification.py --until leaderboard`

> NOTE:
> - 失敗した場合、例外を握りつぶして通すのは禁止です。
> - doctor / lint で検出できる形の「明確なエラー」にしてください。
