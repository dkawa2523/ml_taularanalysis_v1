# T065 dataset_register / preprocess にデータ品質・範囲把握のPlotly可視化を追加（PLOTS）

## 目的
データ登録・前処理段階で、データの範囲/品質/分布を把握できるPlotlyグラフとテーブルをClearML PLOTSに出す。

## 背景 / なぜ必要か
データの品質が不明だと学習結果の解釈ができない。試験段階でもデータ把握の可視化は必須。

## スコープ（やること / やらないこと）
- やる: `src/tabular_analysis/viz/data_profile.py` を作り、軽量な可視化関数を提供
- やる: dataset_register/preprocess から呼び出して PLOTS に出す
- やらない: 重い解析（SHAP等）をデフォルトONにする

## 実装手順（Codexはこの順で実施）
1. `src/tabular_analysis/viz/data_profile.py` を追加:
   - missingness bar
   - numeric histogram（上位K列）
   - categorical top-k bar（上位K列）
   - head sample table（Plotly Table）
2. `src/tabular_analysis/clearml/ui_logger.py`（または既存）に `report_plotly` ラッパを用意し、PLOTSへ統一的に出す。
3. dataset_register:
   - 入力csvを読み、上記グラフをPLOTSに出す
   - 重要値（rows/cols/missing率）をSCALARSにも出す（必要最小）
4. preprocess:
   - rawとprocessedの差が分かる最小の可視化（特徴量数、型、欠損など）
5. docs/62 を更新。


## 受け入れ条件（Acceptance Criteria）
- dataset_register / preprocess の ClearML PLOTS に少なくともテーブル1つ + グラフ1つが表示される。
- 可視化コードが `viz/` に集約され、process側が肥大化しない。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python -m tabular_analysis.cli task=dataset_register run.clearml.enabled=false data.dataset_path=/tmp/ta_rehearsal_data/toy_reg.csv data.target_column=target

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

