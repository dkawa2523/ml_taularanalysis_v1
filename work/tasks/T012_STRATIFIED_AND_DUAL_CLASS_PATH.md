# T012 stratified split + モデルの reg/clf 両対応（class_path マッピング）

## Objective
- 分類で必須になりがちな **層化分割（stratified split）** を preprocess に追加する
- 1つのモデル名（例: ridge）で **回帰/分類の実体を切り替え**できるよう、model_variant の `class_path` を dict で扱えるようにする

---

## Scope
1) `conf/group/split/stratified.yaml` を追加
2) preprocess に `data.split.strategy=stratified` を実装
   - `eval.task_type=classification` のときのみ有効（それ以外は明確にエラー）
   - seed を使い再現可能にする
   - split_hash を安定に計算する（既存方式に合わせる）
3) `registry/models.py` を拡張
   - `model_variant.class_path` が **文字列**でも **dict** でも動くようにする
   - dict の場合は `eval.task_type` で `regression` / `classification` を選ぶ
4) `conf/group/model/ridge.yaml` を更新し、分類時は `RidgeClassifier` を使えるようにする
5) `tools/tests/smoke_classification.py` を拡張
   - `--split stratified` と `--model ridge` の指定で分類学習まで到達できるようにする

---

## Implementation Notes
- 互換性:
  - 既存の `random/group/time` split を壊さない
  - 既存の `class_path: "..."` 形式は引き続きサポートする（破壊的変更禁止）
- stratified の分割器は `sklearn.model_selection.StratifiedShuffleSplit` を推奨
- `ridge` の分類は `sklearn.linear_model.RidgeClassifier` を使用（目的変数が多クラスでも動く）
- 比較可能性の契約:
  - preprocess の split 方式が変われば split_hash は変わる必要がある（混同防止）

---

## Acceptance Criteria
- `data.split.strategy=stratified` で preprocess が完走する（classificationのみ）
- `group/model=ridge` かつ `eval.task_type=classification` で train_model が完走する
- smoke が `--split stratified --model ridge` で通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_classification.py --until train_model --split stratified --model ridge`
