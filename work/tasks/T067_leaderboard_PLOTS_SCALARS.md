# T067 leaderboard：複数指標でスコアリングし、推奨モデルを明確に表示（PLOTS/SCALARS）

## 目的
leaderboard で R2/MSE/RMSE/MAE を統合して推奨モデルを定量的に選定し、ClearML上にテーブル/グラフで表示する。

## 背景 / なぜ必要か
単一指標だと判断に迷うケースが多い。複数指標を統合したスコアリングを導入し、開発者が後で重み等を変更できる設計が必要。

## スコープ（やること / やらないこと）
- やる: scoring weights を conf で管理（開発者が変更可能）
- やる: leaderboard table + top-k bar を PLOTS に表示
- やる: 推奨モデルを Properties と artifact に保存
- やらない: 過度に複雑な多目的最適化（初期はシンプルに）

## 実装手順（Codexはこの順で実施）
1. `conf/leaderboard/scoring.yaml`（または同等）を追加:
   - metrics: [r2, rmse, mae, mse]
   - weights: {r2: +1.0, rmse: -1.0, mae: -0.5, mse: -0.2} など
   - normalization: minmax/robust
2. `src/tabular_analysis/processes/leaderboard.py` を改修:
   - 各train結果を読み取り、指標を揃える
   - normalization + weighted sum で `composite_score` を計算
   - 推奨（best）を選定し、`recommendation.json` と Properties に保存
3. `src/tabular_analysis/viz/leaderboard_plots.py` を追加:
   - leaderboard table（モデル/前処理/各指標/総合スコア）
   - top-k bar（総合スコア）
   - 任意で pareto scatter（R2 vs RMSE）
4. ui_logger で PLOTS 出力し、重要値を Scalars（leaderboard/best_score 等）へ。
5. docs/62 を更新。


## 受け入れ条件（Acceptance Criteria）
- leaderboard の ClearML PLOTS にテーブルが表示され、推奨モデルが分かる。
- 推奨ロジックが conf で変更できる。
- recommendation.json が artifact として残り、Properties でも追える。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python -m tabular_analysis.cli task=leaderboard run.clearml.enabled=false leaderboard.train_task_ids='[]' leaderboard.dry_run=true

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

