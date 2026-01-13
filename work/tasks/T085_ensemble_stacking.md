# T085 [HOTFIX] アンサンブル（stacking）: リーク/不整合/失敗を抑えつつ「比較可能」な指標で leaderboard に載せる

## 背景
- stacking は改善余地が大きいが、実装を誤ると **過大評価（リーク）**や
  **分類の確率不整合**、**一部モデル失敗で全滅**が起きやすい
- 今回は「試験段階で運用できる stacking」を v1 として実装する

---

## 目的
- `process:train_ensemble` に method=`stacking` を追加
- 単体/mean/weighted/stacking を leaderboard で同列比較できる
- stacking は「比較指標」をリークしにくい形で記録し、推薦ロジックに使える

---

## 実装方針（必須要件）

### 1) 候補選定・予測artifact契約・スキップ記録は T083 に完全準拠
- preds_valid 契約が満たせない base は skip
- 分類は `classes.json` が無い/一致しない候補は skip
- 候補>=1 なら degraded success（候補0のみ failed）

### 2) stacking の評価は「リークを避ける」
stacking は meta-model を学習するため、評価設計が重要。
以下の優先順位で **primary_metric として採用する score** を決める。

#### (A) test split が存在する場合（推奨）
- preprocess が `train/valid/test` を提供できるなら:
  1) base は train で学習済み（既存 train_model の前提）
  2) valid で base 予測を集めて meta を fit
  3) test で meta を評価
- この場合、stacking の `primary_metric_source = "test"` として記録し、
  leaderboard も test を優先して比較できる（単体側も test 指標が取れるなら）

#### (B) test split が無い場合（v1 fallback）
- meta 特徴量 `X_meta(valid)` 上で **meta-model の CV 推定値（cv_score）**を primary にする
  - `ensemble.stacking.cv_folds`（例: 5）
  - これを `primary_metric_source = "meta_cv_on_valid"` として記録
- 参考値として `fit_score_on_valid` も計算し artifact に残す（Scalarsの主指標には使わない）

> 重要: 「fitして同じvalidで評価」だけは primary にしない。

### 3) meta-model の選定（依存最小）
- 回帰: `Ridge`（デフォルト）/ `ElasticNet`（オプション）
- 分類: `LogisticRegression`（確率）

### 4) 透明性（再現性）
`ensemble_spec.json` に以下を保存:
- `method: stacking`
- `meta_model`: type + params
- `primary_metric`, `primary_metric_source`
- `included/skipped`
- `meta_training_protocol`（testがある/ない、cv_foldsなど）

meta-model は artifact（pickle/joblib）として保存。

### 5) 失敗時の挙動
- 候補0: failed（no_valid_base_models）
- 候補>=1 だが meta が学習できない:
  - `degraded_to: mean_topk` または `degraded_to: top1` に退避し成功扱い
  - spec に退避理由を残す

---

## 変更内容（実装）

### A) config 追加
- `conf/ensemble/stacking.yaml`（新設）
  - `ensemble.method: stacking`
  - `ensemble.stacking.meta_model: ridge|elasticnet|logreg`
  - `ensemble.stacking.cv_folds: 5`
  - `ensemble.stacking.seed: 42`
  - `ensemble.stacking.require_test_split: false`（trueなら test 無いと skip）

### B) （要確認）split 構造
- 現状 preprocess が test split を持っているか確認
  - ある場合: (A)の評価手順を実装
  - 無い場合: (B)の meta-CV を primary にする

### C) train_ensemble(stacking) 実装
- discovery/filter は T083 と同じ
- meta 特徴量:
  - 回帰: base の `y_pred_valid` を列として結合
  - 分類: base の `proba__<class>` を列として結合（classごと）
- meta 学習:
  - (A) validでfit → testでscore
  - (B) valid上でCV score（primary） + fit_score（参考）
- 予測:
  - stacking モデル bundle は「base ids + meta model」を持つ

### D) ClearML 表示
- task name: `train_ensemble/stacking(k=3)` など
- Scalars:
  - primary_metric（sourceを明記）
  - `ensemble/primary_metric_source`
  - `ensemble/n_included`, `ensemble/n_skipped`
- Plots:
  - base models table
  - skipped summary
  - （分類）meta の係数（上位）など軽い可視化

---

## 受け入れ基準（Acceptance Criteria）
- stacking ensemble が作成される
- primary_metric にリークしにくい値（test or meta-CV）が入り、spec に source が残る
- 一部ベースが落ちてもスキップして成功できる（候補>=1）
- leaderboard で単体/mean/weighted/stacking を同列比較できる

---

## テスト
- `python -m compileall -q src`
- toy データで:
  - train複数モデル → ensemble_stacking → leaderboard
  - `primary_metric_source` が記録される
  - ベースの一部を除外しても動く
