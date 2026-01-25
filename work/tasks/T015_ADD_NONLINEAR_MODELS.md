# T015 モデル追加: KNN / SVR/SVC / GaussianProcess / MLP（計算コスト注意）

## Objective
- テーブルデータ解析で「木以外」の非線形モデルも比較できるようにする
- 追加対象（scikit-learn）:
  - KNN（回帰/分類）
  - SVR（回帰）/ SVC（分類）
  - GaussianProcess（回帰/分類）
  - MLP（回帰/分類）

---

## Scope
1) `conf/group/model/*.yaml` を追加
   - `knn.yaml`
   - `svr.yaml`
   - `svc.yaml`
   - `gaussian_process.yaml`
   - `mlp.yaml`
   ※ `class_path` dict により回帰/分類切替（SVR/SVC は dict で regression/classification を切替）
2) `tools/tests/smoke_model_build_only.py` を追加
   - 学習は重い可能性があるため、まずは「import + instantiate」までを高速に確認する
   - `--task-type` と `--models` を受け取り、各モデルを build して例外が無いことを確認
3) `docs/14_MODEL_CATALOG.md` を更新
   - 使いどころ/計算コスト注意/推奨データサイズ
   - SVC で確率が必要な場合（roc_auc/log_loss）の注意点（probability=True が必要 など）
4) train_model 側の軽微な補正（必要な場合のみ）
   - 分類メトリクスが proba 必須の場合、`predict_proba` が無いモデルの扱いを明確化
     - 例: 「この metric では probability が必要」→ エラーで明示
     - 勝手に metric を変えない

---

## Acceptance Criteria
- 追加したモデル variant を instantiate できる（ライブラリ import / class_path ミスが無い）
- smoke_model_build_only.py が regression / classification で通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_model_build_only.py --task-type regression --models knn,svr,gaussian_process,mlp`
- `python tools/tests/smoke_model_build_only.py --task-type classification --models svc,knn,gaussian_process,mlp`
