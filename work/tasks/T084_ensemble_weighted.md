# T084 [HOTFIX] アンサンブル（weighted）: 失敗/確率不整合を考慮しつつ、重み推定を安全に実装

## 背景
- weighted は mean_topk より改善する場合がある一方、
  - 分類で確率が揃わない
  - 候補が多いと探索が難しい
  - 一部モデルが落ちると全体が落ちる
  など運用上の事故が起きやすい

---

## 目的
- `process:train_ensemble` に method=`weighted` を追加（または別実装でも可）
- **候補フィルタ/スキップ記録は T083 と同一契約**で統一
- leaderboard で単体/mean_topk/weighted を同列比較できる

---

## 実装方針（必須要件）

### 1) 候補選定・予測artifact契約・スキップ記録は T083 に完全準拠
- `ensemble_spec.json` に included/skipped を必ず残す
- base が一部落ちても落とさない（候補>=1なら degraded success）

### 2) weighted は「top_k の上限」を持つ（探索が破綻しないため）
- `ensemble.weighted.top_k_max: 5`（デフォルト）
- top_k が大きい場合は自動で `min(top_k, top_k_max)` に丸める

### 3) 重み推定アルゴリズム（依存最小・安全）
優先順位:
1. **回帰**: 非負制約付き最小二乗
   - `sklearn.linear_model.LinearRegression(positive=True, fit_intercept=False)` を使えるなら採用
   - 使えない場合は `Ridge(fit_intercept=False)` で近似し、負の重みは 0 にクリップ
   - 最後に `weights = weights / weights.sum()`
2. **分類**: 確率合成に対して目的関数最適化
   - `y_pred = sum(w_i * proba_i)`
   - 目的関数は `eval.primary_metric`（AUC/LogLoss/F1 等）
   - 安定しないためデフォルトは `random_simplex` を推奨

3. fallback（回帰/分類共通）: **random simplex search**
   - Dirichlet サンプルで `n_samples` 回評価
   - `seed` を保存し再現可能にする

> 注意: 分類は必ず **classes順の整合**が必要。classesが一致しない候補は skip。

### 4) 透明性（再現性）
- `ensemble_spec.json` に以下を保存
  - `method: weighted`
  - `weights: {train_task_id: weight}`
  - `search: linear|random_simplex`
  - `n_samples`, `seed`
  - `objective_metric`, `direction`
  - `included/skipped`

### 5) 失敗条件
- 候補0: failed（no_valid_base_models）
- 候補>=1 かつ weight 推定が不可能:
  - fallback に落としてでも推定する
  - それも無理なら **その時点の最良単体（top1）に退避**して成功扱い
    - spec に `degraded_to: top1` を記録

---

## 変更内容（実装）

### A) config 追加
- `conf/ensemble/weighted.yaml`（新設）
  - `ensemble.method: weighted`
  - `ensemble.weighted.search: linear|random_simplex`
  - `ensemble.weighted.n_samples: 1500`
  - `ensemble.weighted.seed: 42`
  - `ensemble.weighted.top_k_max: 5`

### B) train_ensemble(weighted) 実装
- T083 と同じ discovery/filter を使って候補選定
- preds_valid を読み込み、重み推定
- 合成して metrics 計算
- bundle/spec/metrics を保存

### C) ClearML 表示
- task name: `train_ensemble/weighted(k=3)` のように識別可能
- Plots:
  - base models table
  - weights table
  - skipped summary
- Scalars:
  - primary_metric
  - `ensemble/n_included`, `ensemble/n_skipped`

---

## 受け入れ基準（Acceptance Criteria）
- weighted ensemble が作成される
- 一部モデルが落ちてもスキップして成功できる（候補>=1）
- weights と探索条件が spec に残る
- leaderboard で単体/mean/weighted が同列比較できる

---

## テスト
- `python -m compileall -q src`
- toy データで:
  - train複数モデル → ensemble_weighted → leaderboard
  - weights が出る / degraded_to の場合も spec に残る

---

## Update (2026-01-13)
- mean_topk (T083) の実装が前提のため後段対応
- refactor plan の Phase 3 (T101) に統合

## Update (2026-01-14)
- weighted を train_ensemble に実装。回帰は linear/ridge を試して失敗時は random simplex、分類は random simplex 探索。`src/tabular_analysis/processes/train_ensemble.py`
- `ensemble.weighted.*` を設定追加。`conf/ensemble/base.yaml` / `conf/ensemble/weighted.yaml`
- spec に weights と探索設定を記録し、ClearML では weights table を出力。
