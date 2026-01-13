# T070 infer.mode=optimize：Optuna最適化 + child推論タスク生成 + Optuna可視化をPLOTSに表示

## 目的
optimize 推論を追加し、Optunaで探索→trialごとのchild推論タスク生成→サマリーで最適化可視化/上位条件テーブルをPLOTSに出す。

## 背景 / なぜ必要か
現場では『入力条件をどう振れば目的出力が最大化するか』を探索したい。試験段階でOptunaを用いた形を作っておくと将来拡張しやすい。

## スコープ（やること / やらないこと）
- やる: optuna を optional dependency として扱い、無い場合は明確にfail
- やる: Optuna plots（history/parallel/importance/response surface）をPlotlyでPLOTSへ
- やる: trialをchild task化し、入力→出力を追える
- やらない: 推論を pipeline_controller にしない

## 実装手順（Codexはこの順で実施）
1. `infer.mode=optimize` を実装:
   - Optunaで study を作成（sampler, n_trials, direction）
   - 探索空間を conf で定義（連続/離散）
2. trialごとに child task を clone/enqueue（infer.mode=single相当）し、結果を集めて objective を評価。
   - 失敗trialは記録し、studyに反映（可能な範囲で）
3. summary で Optuna 可視化をPLOTSへ:
   - optimization_history（log scale option）
   - parallel_coordinate
   - param_importances
   - contour/response surface（可能な範囲）
4. 上位K trial の入力→出力テーブルをPLOTSへ。
5. HyperParameters:
   - Optimize セクションに探索空間、sampler、n_trials、objective を載せる。
6. docs/64 と docs/62 を更新。


## 受け入れ条件（Acceptance Criteria）
- optimize 実行で summary + trial child tasks が ClearML に作成される。
- summary の PLOTS に Optunaグラフが表示される。
- 上位K条件の入力→出力テーブルが PLOTS に表示される。
- Optunaが無い環境では明確にエラー（依存追加案内）し、黙って落ちない。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python -m tabular_analysis.cli task=infer run.clearml.enabled=false infer.mode=optimize infer.dry_run=true

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

