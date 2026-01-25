# T014 モデル追加: RandomForest / ExtraTrees / GradientBoosting + feature importance 統一

## Objective
- 木系モデルを追加して、非線形の強いベースラインを確保する
- 追加対象（scikit-learn）:
  - RandomForest（回帰/分類）
  - ExtraTrees（回帰/分類）
  - GradientBoosting（回帰/分類）
- 併せて、train_model における **feature importance 出力を統一**し、UI/Artifacts 契約を改善する

---

## Scope
1) `conf/group/model/*.yaml` を追加
   - `random_forest.yaml`
   - `extra_trees.yaml`
   - `gradient_boosting.yaml`
   ※ 回帰/分類両対応は `class_path` dict を使用（T012 の仕様）
2) train_model に feature importance 抽出を追加（軽量）
   - 優先順:
     - `feature_importances_` があれば利用（木系/GBDT）
     - `coef_` があれば利用（線形、絶対値などの方針を docs に明記）
   - 出力:
     - `feature_importance.csv`（最低限）
   - ClearML enabled 時は artifact としてアップロード（docs/03 契約に沿う）
3) `tools/tests/smoke_train_regression_model.py` を拡張
   - `--expect-feature-importance` のとき、`feature_importance.csv` の存在を検証
4) `docs/14_MODEL_CATALOG.md` を更新

---

## Implementation Notes
- 木系はデフォルトパラメータで計算が重くなりがちなので、toy smoke で止まらない設定にする
  - `n_estimators` は大きすぎない（例: 200 以下）
  - `max_depth` / `min_samples_leaf` を適切に
- 特徴量名:
  - preprocess の出力（エンコード後）で特徴量名が増えるので、可能なら `preprocess_bundle` 側から feature_names を取得して揃える
  - 取れない場合でも CSV は出す（列名は `feature_i` でも可。ただし docs に記載）

---

## Acceptance Criteria
- `group/model=random_forest` の回帰 train_model が完走
- `feature_importance.csv` が出力される（random_forest で確認）
- smoke が `--expect-feature-importance` で通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_train_regression_model.py --model random_forest --expect-feature-importance`
