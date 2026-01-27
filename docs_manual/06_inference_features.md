# 本コードの推論機能

## 1. 単一条件 推論
| 項目 | 内容 |
| --- | --- |
| 想定入力情報 | `infer.model_id` または `infer.train_task_id` + `infer.input_path`/`infer.input_json` |
| 出力内容 | `predictions.*`、入力→出力テーブル（Plotly）、必要に応じて drift_report |
| 想定ユースケース | 単発予測、モデル検証、UI確認 |

## 2. 範囲 Grid 実行（batch）
| 項目 | 内容 |
| --- | --- |
| 想定入力情報 | `infer.batch.inputs_path`（csv/parquet） or `infer.batch.inputs_json` |
| 出力内容 | 子タスクごとの予測 + summary（分布/上位サンプル） |
| 想定ユースケース | 条件を複数並べて比較、シナリオ分析 |

## 3. 最適化（Optuna）
| 項目 | 内容 |
| --- | --- |
| 想定入力情報 | `infer.optimize.search_space`（探索空間）+ `infer.optimize.n_trials` |
| 出力内容 | Optuna可視化、上位条件テーブル、best条件 |
| 想定ユースケース | KPI最大化/最小化条件の探索 |

### 3.1 最適化サンプラー
| サンプラー名 | 概要 | メリット | 想定利用ケース | ライブラリ |
| --- | --- | --- | --- | --- |
| tpe | ベイズ最適化系 | 少試行で効率的 | 標準運用 | Optuna |
| random | ランダム探索 | 実装シンプル | ベースライン | Optuna |
| cmaes | 連続最適化 | 連続変数に強い | 連続空間最適化 | Optuna |

### 3.2 目的変数の Loss
- optimize では `infer.optimize.objective.key` で目的値を指定します（例: `prediction`）。
- `infer.optimize.direction` が `maximize`/`minimize` を決めるため、**損失最小化の場合は minimize** を使います。
- 予測値そのものではなく「損失」を最小化したい場合は、
  - 目的値として `loss` を明示的に出力する（カスタム出力）
  - または `direction=minimize` にして対象をスカラー化する

