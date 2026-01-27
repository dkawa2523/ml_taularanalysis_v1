# 設定ファイルの説明

## 1. 設定ファイル一覧
| ファイル/ディレクトリ | 目的 | 読み込みタイミング | 関連機能 |
| --- | --- | --- | --- |
| `conf/config.yaml` | Hydraの全体デフォルト | 全タスク起動時 | すべて |
| `conf/run/base.yaml` | 実行/ SPDML設定 | 全タスク | 実行モード/追跡性 |
| `conf/run/alerts/base.yaml` | アラート設定 | alerting使用時 | ops/alerting |
| `conf/data/base.yaml` | データ入力 | dataset_register/preprocess/train/infer | データ読み込み |
| `conf/data/quality/base.yaml` | 品質ゲート | dataset_register/preprocess/infer | 品質チェック |
| `conf/eval/base.yaml` | 評価/指標 | train/leaderboard | metrics/比較 |
| `conf/ensemble/base.yaml` | アンサンブル | train_ensemble | ensemble方式 |
| `conf/leaderboard/scoring.yaml` | スコアリング | leaderboard | 推奨ロジック |
| `conf/exec_policy/base.yaml` | 実行制限/queue | pipeline | 実行制御 |
| `conf/monitor/base.yaml` | ドリフト監視 | infer/drift | 監視指標 |
| `conf/viz/base.yaml` | 可視化 | 各タスク | Plot出力 |
| `conf/task/*/base.yaml` | タスク別設定 | 対象タスク | task挙動 |
| `conf/group/*/*.yaml` | バリアント | preprocess/model/split/infer | 変種管理 |
| `conf/pipeline/model_sets/*.yaml` | model_set | pipeline | モデルセット |
| `conf/clearml/*` | SPDML UI/テンプレ | SPDML連携 | UI規約 |
| `conf/ops/*` | 運用ポリシー | usecase_id等 | 命名/保存 |

## 2. 主要 YAML 変数一覧

### 2.1 `conf/run/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `run.usecase_id` | str/null | usecase識別子 | null | nullなら自動生成 |
| `run.output_dir` | str | 出力先 | `outputs/${now:%Y%m%d_%H%M%S}` | 運用で固定すると比較しやすい |
| `run.schema_version` | str | 追跡スキーマ | v1 | 変更時は下位互換に注意 |
| `run.grid_run_id` | str/null | grid識別子 | null | pipelineが自動生成 |
| `run.retrain_run_id` | str/null | retrain識別子 | null | retrainで付与 |
| `run.clearml.enabled` | bool | SPDML連携ON/OFF | false | logging/agent時はtrue |
| `run.clearml.execution` | str | 実行モード | local | local/logging/agent/clone/pipeline_controller |
| `run.clearml.queue_name` | str/null | SPDML queue | null | agent/ controller時に必須 |
| `run.clearml.code_ref.mode` | str | code参照 | branch | template運用ではbranch推奨 |
| `run.clearml.project_root` | str | SPDML project root | MFG | 環境に合わせて変更 |
| `run.clearml.template_usecase_id` | str | テンプレ用usecase | TabularAnalysis | テンプレ探索に使用 |
| `run.clearml.pipeline.project_mode` | str | pipeline project表示 | subproject | UI表示方針に合わせる |
| `run.clearml.reporting.*` | bool | plots/scalars/tables | true | UI負荷に合わせ調整 |

### 2.2 `conf/run/alerts/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `run.alerts.enabled` | bool | アラート有効化 | false | 開発時はfalse推奨 |
| `run.alerts.sinks.file.path` | str/null | ローカル出力先 | null | run.output_dirと併用 |
| `run.alerts.sinks.webhook.url` | str/null | Webhook通知先 | null | 本番のみ設定 |

### 2.3 `conf/data/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `data.dataset_path` | str/null | rawデータパス | null | dataset_registerで使用 |
| `data.raw_dataset_id` | str/null | SPDML Dataset ID | null | dataset_register後に指定 |
| `data.processed_dataset_id` | str/null | processed dataset ID | null | preprocessを省略する時のみ |
| `data.target_column` | str | 目的変数名 | target | 必須列が存在すること |
| `data.id_columns` | list[str] | ID列除外 | [] | リーク防止に使用 |
| `data.drop_columns` | list[str] | 明示除外列 | [] | 派生特徴の整理に使用 |
| `data.split.strategy` | str | split方式 | random | time/stratified/groupを選択 |
| `data.split.test_size` | float | テスト割合 | 0.2 | 0.1〜0.3で調整 |
| `data.split.seed` | int | split seed | 42 | 再現性確保のため固定 |
| `data.split.group_column` | str/null | group split列 | null | group時のみ |
| `data.split.time_column` | str/null | time split列 | null | time時のみ |

### 2.4 `conf/data/quality/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `data.quality.mode` | str | warn/fail/off | warn | 本番はfail推奨 |
| `data.quality.enabled` | bool | 品質チェック | true | 高速化したい場合off |
| `data.quality.max_rows_scan` | int | 走査上限 | 50000 | 巨大データで調整 |
| `data.quality.thresholds.*` | float/int | 閾値群 | 既定値 | ドメインに合わせる |

### 2.5 `conf/eval/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `eval.task_type` | str | regression/classification | regression | 目的に合わせる |
| `eval.primary_metric` | str | 主指標 | rmse | leaderboard順位に使用 |
| `eval.direction` | str | maximize/minimize/auto | auto | auto推奨 |
| `eval.cv_folds` | int | CV分割 | 5 | 0でholdoutのみ |
| `eval.seed` | int | 乱数seed | 42 | 再現性確保 |
| `eval.metrics.regression` | list[str] | 回帰指標 | [r2,mse,rmse,mae] | 指標追加可 |
| `eval.uncertainty.enabled` | bool | 予測区間 | false | 誤差帯が必要ならON |
| `eval.calibration.enabled` | bool | 校正 | false | 分類のみ |
| `eval.imbalance.enabled` | bool | 不均衡対応 | false | 分類のみ |

### 2.6 `conf/task/preprocess/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `preprocess.variant` | str | 前処理バリアント | ${preprocess_variant.name} | conf/group/preprocess を参照 |
| `preprocess.numeric_impute` | str | 数値欠損補完 | mean | mean/medianなど |
| `preprocess.categorical_impute` | str | カテゴリ欠損補完 | most_frequent | 文字列化を避ける |
| `preprocess.categorical.encoding` | str | 高カーディナリティ処理 | onehot | frequency/hashing/target_mean_oof |

### 2.7 `conf/task/train_model/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `train.model` | str | モデルバリアント | ${model_variant.name} | conf/group/model を参照 |
| `train.params` | dict | 追加パラメータ | {} | バリアントを上書き |
| `train.inputs.preprocess_run_dir` | str/null | preprocess run_dir | null | local運用時に利用 |
| `train.inputs.preprocess_task_id` | str/null | preprocess task_id | null | SPDMLから復元時 |

### 2.8 `conf/task/infer/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `infer.model_id` | str/null | SPDML Model ID | null | 推奨は model_id 指定 |
| `infer.train_task_id` | str/null | trainタスクID | null | model_idが無い時 |
| `infer.mode` | str | single/batch/optimize | single | conf/group/infer_modeで切替 |
| `infer.input_path` | str/null | 単体入力 | null | csv/parquet |
| `infer.input_json` | dict/null | 単体入力(JSON) | null | CLIからはjson文字列 |
| `infer.batch.inputs_path` | str/null | batch入力 | null | csv/parquet |
| `infer.batch.max_children` | int/null | 子タスク上限 | null | タスク爆発防止 |
| `infer.optimize.n_trials` | int | 試行回数 | 20 | 探索コストに注意 |
| `infer.optimize.sampler` | str | サンプラー | tpe | tpe/random/cmaes |
| `infer.optimize.search_space` | list | 探索空間 | [] | optimize時は必須 |

### 2.9 `conf/ensemble/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `ensemble.enabled` | bool | アンサンブル有効化 | false | pipelineに合わせる |
| `ensemble.method` | str | 基本方式 | mean_topk | mean_topk/weighted/stacking |
| `ensemble.top_k` | int | 上位K平均 | 3 | 0で全使用 |
| `ensemble.weighted.n_samples` | int | 重み探索数 | 1500 | 多すぎると重い |
| `ensemble.stacking.meta_model` | str | メタモデル | ridge | conf/group/model参照 |

### 2.10 `conf/leaderboard/scoring.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `scoring.metrics` | list[str] | 複合スコア対象 | [r2,rmse,mae,mse] | metric追加可 |
| `scoring.weights.*` | float | 重み | r2=1.0 他負 | 方向に注意 |
| `scoring.normalization` | str | 正規化 | minmax | robustも可 |

### 2.11 `conf/exec_policy/base.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `exec_policy.limits.max_jobs` | int | 最大学習数 | 50 | タスク爆発防止 |
| `exec_policy.limits.max_models` | int | 表示上限 | 10 | report/leaderboard向け |
| `exec_policy.limits.max_hpo_trials` | int | HPO上限 | 0 | 0は無制限 |
| `exec_policy.queues.default` | str/null | デフォルトqueue | ${run.clearml.queue_name} | agent実行時に必須 |
| `exec_policy.queues.model_variants` | dict | モデル別queue | {} | 重いモデル分離 |

### 2.12 `conf/pipeline/model_sets/*.yaml`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `task_type` | str | regression/classification | regression | model_setの対象 |
| `auto` | bool | 自動列挙 | true | registry基準で列挙 |
| `variants` | list[str] | 明示リスト | [] | 固定運用にする |
| `exclude` | list[str] | 除外モデル | [] | optional依存を除外 |

### 2.13 `conf/clearml/*`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `run.clearml.project_layout.*` | dict | SPDML階層 | 既定値 | プロジェクト階層を統一 |
| `run.clearml.hyperparams.sections` | list | UIセクション | 既定値 | 必要最小に絞る |
| `conf/clearml/templates.yaml` | dict | テンプレ定義 | 既定値 | clone/pipeline_controller運用 |

### 2.14 `conf/ops/*`
| 変数名 | 型 | 内容 | デフォルト値 | 入力tips |
| --- | --- | --- | --- | --- |
| `run.usecase_id_policy.*` | dict | usecase自動生成 | test_dataset_timestamp | 本番用policyを追加 |
| `run.clearml.policy.tags` | list | 追加タグ | solution:tabular-analysis | 検索用に短く |
| `ops.processed_dataset.store_features` | bool | X/y保存 | true | 大規模データはfalse |
