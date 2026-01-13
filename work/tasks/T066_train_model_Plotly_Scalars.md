# T066 train_model（回帰）の指標テーブル・散布図などPlotly可視化とScalars出力を追加

## 目的
train_model の結果を、R2/MSE/RMSE/MAEをScalars + PLOTS（テーブル/散布図）として表示し、モデル比較・解釈を可能にする。タスク名/タグもモデル判別可能にする。

## 背景 / なぜ必要か
PLOTSが空だとモデル選定ができない。タスク名だけで条件が分からないと運用が破綻する。

## スコープ（やること / やらないこと）
- やる: 回帰評価の標準指標を統一
- やる: y_true vs y_pred, residual, metrics table を Plotly で出す
- やる: task titleにモデル略称、tagsにdataset/preprocess/modelを追加
- やらない: 過度な可視化（重い）を標準ONにする

## 実装手順（Codexはこの順で実施）
1. `src/tabular_analysis/metrics/regression.py`（または既存）を確認し、R2/MSE/RMSE/MAEを一括計算する関数を用意（既存があれば統一）。
2. `src/tabular_analysis/viz/regression_plots.py` を追加:
   - metrics table（Plotly Table）
   - y_true vs y_pred scatter + y=x
   - residual plot（任意）
3. train_model process:
   - metrics を Scalars に出す（metrics/r2等）
   - PLOTS に table/scatter を出す
   - 可能なら feature importance を PLOTS に出す（対応モデルのみ）
4. ClearML task naming/tags:
   - task名に `train__{model_abbr}__pp={preprocess}__ds={raw_short}` を入れる
   - tagsに `model:<abbr>`, `preprocess:<variant>`, `dataset:<raw_id>` を追加
   - ルールは `clearml/naming.py` へ集約
5. docs/62, docs/66 を更新。


## 受け入れ条件（Acceptance Criteria）
- train_model の ClearML PLOTS に metrics table と散布図が表示される。
- train_model の Scalars に R2/MSE/RMSE/MAE が表示される。
- ClearML上でタスク名・タグからモデル/前処理/データが分かる。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python -m tabular_analysis.cli task=train_model run.clearml.enabled=false data.dataset_path=/tmp/ta_rehearsal_data/toy_reg.csv data.target_column=target group/model=linear_regression group/preprocess=stdscaler_ohe

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

