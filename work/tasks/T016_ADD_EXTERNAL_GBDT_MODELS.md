# T016 外部GBDT: LightGBM / XGBoost / CatBoost（optional deps + graceful error）

## Objective
- 高精度になりやすい外部GBDT系モデルを追加し、比較できるようにする
- 追加対象（optional dependency）:
  - LightGBM（既存だが回帰専用になっている可能性 → 回帰/分類対応へ）
  - XGBoost
  - CatBoost
- optional 依存が無い環境でも **落ち方を明確にし**、Codex 開発や業務利用で止まりにくくする

---

## Scope
1) `pyproject.toml` の extras を更新
   - `models` extras に `catboost>=1.2` を追加
   - 既存の `lightgbm/xgboost` の最小要求を表（docs/14）に合わせる
2) `conf/group/model/*.yaml` を整備
   - `lgbm.yaml`: class_path を dict 化して回帰/分類対応
   - `xgboost.yaml`: 新規追加（reg/clf）
   - `catboost.yaml`: 新規追加（reg/clf）
3) `registry/models.py` を強化
   - optional ライブラリが無い場合:
     - ImportError を握りつぶさず、**インストール手順を含む明確な例外**にする
     - 例: `pip install -e ".[models]"`
   - ただし verify は「ライブラリ有無に依存せず通る」必要があるため、テスト側で両対応にする
4) テスト追加: `tools/tests/check_optional_models.py`
   - 指定モデル（lgbm/xgboost/catboost）を build し、
     - lib が無ければ「想定した MissingOptionalDependencyError」であること
     - lib があれば instantiate できること
   を確認して PASS とする

---

## Acceptance Criteria
- optional dependency が無い環境でも、該当モデル選択時に「何をインストールすべきか」が明確に出る
- optional dependency がある環境ではモデルが build できる
- check_optional_models.py が通る（環境に依存せず）

---

## Verification（runner 側で実行）
- `python tools/tests/check_optional_models.py --models lgbm,xgboost,catboost`
