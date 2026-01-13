# T068 infer：Configuration/HyperParametersに入力条件・モデル来歴を表示し、PLOTSに入力→出力テーブルを出す

## 目的
infer の UI を改善し、推論条件（mode/入力/モデル）とモデル来歴（学習データセット/前処理/学習モデル）を把握できるようにする。出力は PLOTS のテーブル中心。

## 背景 / なぜ必要か
現状 infer の設定が ClearML UI で追えず、推論結果の解釈ができない。モデルがどのデータで学習されたか確認できないと事故る。

## スコープ（やること / やらないこと）
- やる: infer hparams をカテゴリ別に表示（Inputs/Model/Dataset/Execution/Optimize等）
- やる: model bundle/manifest から provenance を読み取り表示
- やる: input→output の Plotly Table を PLOTS に表示（DEBUGは使わない）
- やらない: pipeline_controller を推論に持ち込む（禁止）

## 実装手順（Codexはこの順で実施）
1. infer process を調査し、`infer.mode=single/batch/optimize` を想定した config を整理（optimize/batchは後続T069/T070）。
2. `src/tabular_analysis/clearml/hparams.py` の infer 接続を強化:
   - Inputs: mode, input source（path/json）
   - Model: model_id, model_abbr
   - Dataset: provenance（train_task_id, raw_dataset_id, preprocess_variant 等）
3. `src/tabular_analysis/clearml/ui_logger.py` に Plotly Table を PLOTS に出す helper を追加（入力と出力のテーブル）。
4. model provenance:
   - 既存の `model_bundle/manifest.json` 等があればそこから抽出
   - 無い場合、train_model 側で model bundle に provenance を追加する（最小キー）
5. docs/62, docs/64 を更新。


## 受け入れ条件（Acceptance Criteria）
- infer の HyperParameters がセクション分割され、入力条件と model_id が見える。
- infer の PLOTS に入力→出力テーブルが表示される。
- provenance が UI で追える（少なくとも train_task_id / dataset_id / preprocess）。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python -m tabular_analysis.cli task=infer run.clearml.enabled=false infer.mode=single infer.dry_run=true

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

