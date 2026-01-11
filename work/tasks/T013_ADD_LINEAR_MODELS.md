# T013 モデル追加: LinearRegression / Lasso / ElasticNet（回帰ベースライン強化）

## Objective
- scikit-learn の基本線形モデルを追加して、回帰のベースライン/比較を強化する
- 追加対象:
  - LinearRegression
  - Lasso
  - ElasticNet

> Ridge は既存（T012で回帰/分類両対応化）  
> LogisticRegression は T011 で最低限の分類モデルとして追加済み

---

## Scope
1) `conf/group/model/*.yaml` を追加
   - `linear_regression.yaml`
   - `lasso.yaml`
   - `elasticnet.yaml`
2) `docs/14_MODEL_CATALOG.md` を更新（追加モデルの注意点・使いどころ）
3) verify 強化のため `tools/tests/smoke_train_regression_model.py` を追加
   - `--model <variant>` を受け取り、toy データで
     - dataset_register
     - preprocess（stdscaler_ohe）
     - train_model
     まで実行して契約（out/manifest）を検証

---

## Implementation Notes
- Lasso/ElasticNet は収束に時間がかかる場合があるため、デフォルトパラメータは安全側に設定する
  - `max_iter` を入れる
  - `random_state` を seed に合わせる（sklearn 実装に応じて）
- LinearRegression は deterministic なので params は最小でもよい
- feature importance はこの段階では必須化しない（T014 で統一する）

---

## Acceptance Criteria
- `group/model=linear_regression` の train_model が完走
- `group/model=elasticnet` の train_model が完走
- smoke_train_regression_model.py が通る（モデル指定で動く）

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_train_regression_model.py --model linear_regression`
- `python tools/tests/smoke_train_regression_model.py --model elasticnet`
