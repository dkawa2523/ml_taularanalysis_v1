# T061 pipeline（学習回帰）を「dataset_id入力前提」に修正し、dataset_registerを独立運用にする

## 目的
学習pipelineが dataset_register から始まらず、`data.raw_dataset_id` を入力に preprocess→train×N→leaderboard を実行できるようにする。dataset_register は別コマンドで実行する運用に寄せる。

## 背景 / なぜ必要か
現状はpipelineがデータ登録を内包しがちで、運用上の冗長（毎回登録）や、既存Datasetを使う際の障害になる。試験段階でも本番でも、dataset_registerは独立させる方が運用設計しやすい。

## スコープ（やること / やらないこと）
- やる: pipeline config/実装を見直し、raw_dataset_id入力を必須化（または強推奨）
- やる: docs/60 を正にして実装を合わせる
- やらない: ml-platform 側の仕様変更（solution側で吸収）

## 実装手順（Codexはこの順で実施）
1. `src/tabular_analysis/processes/pipeline.py`（または該当箇所）を調査し、train pipeline の entry を `data.raw_dataset_id` 入力に寄せる。
   - `pipeline.run_dataset_register` をデフォルト false にする（config側）。
   - dataset_register を実行する場合は明示フラグでのみ実行。
2. preprocess step が `data.raw_dataset_id` を必ず受け取るようにする。
   - dataset_register をスキップした場合でも preprocess が動くこと。
3. train step 群は preprocess の出力（processed_dataset_id）を入力として使う（前処理の再fitを避ける）。
4. docs/60 を更新し、実装と一致させる。


## 受け入れ条件（Acceptance Criteria）
- `task=pipeline/train_regression` が `data.raw_dataset_id=<id>` だけで preprocess→train→leaderboard まで通る。
- `pipeline.run_dataset_register=true` のときのみ dataset_register が実行される。
- 実装が docs/60 と矛盾しない。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python -m tabular_analysis.cli task=pipeline/train_regression run.clearml.enabled=false data.raw_dataset_id=dummy pipeline.dry_run=true

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

