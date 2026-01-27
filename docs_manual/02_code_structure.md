# コード構成

## 1. ディレクトリ構成
| ディレクトリ | 役割 | 主な内容 | 変更が必要になりやすいケース |
| --- | --- | --- | --- |
| `src/` | 実装本体 | タスク実装、SPDML連携、学習/推論ロジック | 機能追加・バグ修正・仕様変更 |
| `conf/` | 設定 | Hydra設定、タスク/モデル/前処理/実行モード | 新しいモデル/前処理/運用切替 |
| `tools/` | 運用補助 | SPDMLテンプレ生成、リハーサル/検証スクリプト | 運用手順変更・テンプレ更新 |
| `serving/` | 推論API | APIサーバ/設定/認証 | Serving機能追加 |
| `artifacts/` | 参照用成果物 | 仕様テンプレ、サンプル | 仕様更新 |
| `outputs/` | 実行成果物 | run出力（ローカル） | 実行後の確認・保管 |
| `docs/` | 既存仕様書 | 契約/方針/運用ガイド | 仕様を変更する時 |
| `docs_manual/` | 本マニュアル | MkDocs用の整理版 | 文書を更新する時 |
| `requirements/` | 依存管理 | base/models などの依存一覧 | 依存追加・更新 |

## 2. 各ディレクトリ内のファイル説明
### 2.1 `src/tabular_analysis/` 配下（主要ファイル）
| ファイル | 役割 | 主な入出力 | 関連設定/依存 | 変更が必要になりやすいケース |
| --- | --- | --- | --- | --- |
| `src/tabular_analysis/cli.py` | Hydra CLI 入口 | CLI→各タスク実行 | `conf/config.yaml` | 実行コマンドやタスク追加 |
| `src/tabular_analysis/platform_adapter.py` | SPDML/Platform連携の集約 | Task/Artifact/Model/Dataset/Tags | `conf/run/base.yaml` | SPDML仕様・追跡性変更 |
| `src/tabular_analysis/doctor.py` | 出力/契約 lint | run_dir 検証 | `docs/03_*` | 仕様チェック強化 |
| `src/tabular_analysis/ops/clearml_identity.py` | usecase_id/プロジェクト解決 | usecase_id/プロジェクト名 | `conf/ops/usecase_id_policy/*` | 命名・タグ方針変更 |
| `src/tabular_analysis/ops/data_quality.py` | データ品質ゲート | 品質レポート/例外 | `conf/data/quality/base.yaml` | 品質基準変更 |
| `src/tabular_analysis/ops/alerting.py` | アラート出力 | 監視イベント | `conf/run/alerts/base.yaml` | 通知経路変更 |
| `src/tabular_analysis/ops/local_orchestrator.py` | ローカル一括実行 | dataset→pipeline | `conf/task/*` | ローカル統合運用変更 |
| `src/tabular_analysis/ops/manage_clearml_templates.py` | SPDMLテンプレ生成 | template tasks | `conf/clearml/templates.yaml` | テンプレ更新 |
| `src/tabular_analysis/ops/ui_contract_lint.py` | UI契約lint | SPDML UIチェック | `docs/03_*` | UI契約変更 |
| `src/tabular_analysis/clearml/datasets.py` | SPDML Dataset登録/取得 | dataset_id | `conf/clearml/project_layout.yaml` | データセット仕様変更 |
| `src/tabular_analysis/clearml/hparams.py` | HyperParams抽出/接続 | Sectioned params | `conf/clearml/hyperparams_sections.yaml` | UI表示項目変更 |
| `src/tabular_analysis/clearml/naming.py` | SPDML task名生成 | task name | `docs/66_*` | 命名規約変更 |
| `src/tabular_analysis/clearml/ui_logger.py` | SPDMLへのログ/Plot出力 | Scalars/Plots | `conf/viz/base.yaml` | 可視化拡張 |
| `src/tabular_analysis/clearml/templates.py` | テンプレ解決 | template task_id | `conf/clearml/templates.yaml` | テンプレ検索変更 |
| `src/tabular_analysis/clearml/template_manager.py` | テンプレ管理ユーティリティ | template operations | `conf/clearml/templates.yaml` | 管理機能追加 |
| `src/tabular_analysis/processes/dataset_register.py` | rawデータ登録 | raw_dataset_id | `conf/task/dataset_register/base.yaml` | 入力形式/登録仕様変更 |
| `src/tabular_analysis/processes/preprocess.py` | 前処理 & processed dataset | processed_dataset_id | `conf/task/preprocess/base.yaml` | 前処理仕様変更 |
| `src/tabular_analysis/processes/train_model.py` | 学習 | model_id, metrics | `conf/task/train_model/base.yaml` | モデル追加/評価追加 |
| `src/tabular_analysis/processes/train_ensemble.py` | アンサンブル学習 | ensemble model_id | `conf/ensemble/base.yaml` | アンサンブル方式追加 |
| `src/tabular_analysis/processes/leaderboard.py` | 比較/推奨 | leaderboard.csv | `conf/leaderboard/scoring.yaml` | 推奨ロジック変更 |
| `src/tabular_analysis/processes/infer.py` | 推論（single/batch/optimize） | predictions, plots | `conf/task/infer/base.yaml` | 推論モード拡張 |
| `src/tabular_analysis/processes/pipeline.py` | pipeline接着 | plan.json/run_summary | `conf/task/pipeline/base.yaml` | 実行順/計画仕様変更 |
| `src/tabular_analysis/processes/retrain.py` | 再学習フロー | retrain_run_id | `conf/task/retrain/*` | 再学習運用変更 |
| `src/tabular_analysis/processes/drift_report.py` | ドリフトレポート | drift_report | `conf/monitor/base.yaml` | ドリフト基準変更 |
| `src/tabular_analysis/registry/models.py` | モデル生成 | model instance | `conf/group/model/*` | モデル追加/optional依存追加 |
| `src/tabular_analysis/registry/preprocessors.py` | 前処理パイプライン生成 | transformer | `conf/group/preprocess/*` | 前処理追加 |
| `src/tabular_analysis/registry/metrics.py` | 指標実装 | metric function | `conf/eval/base.yaml` | 指標追加 |
| `src/tabular_analysis/registry/tabpfn.py` | TabPFN関連 | weights resolve | `conf/group/model/tabpfn.yaml` | TabPFN仕様変更 |
| `src/tabular_analysis/registry/model_registry_state.py` | model registry 状態 | cache/state | 内部 | レジストリ拡張 |
| `src/tabular_analysis/metrics/regression.py` | 回帰指標 | r2/mse/rmse/mae | scikit-learn | 回帰指標追加 |
| `src/tabular_analysis/feature_engineering/categorical.py` | 高カーディナリティ処理 | encoding | scikit-learn | エンコード方式追加 |
| `src/tabular_analysis/monitoring/drift.py` | ドリフト指標 | psi/ks | `conf/monitor/base.yaml` | 監視指標変更 |
| `src/tabular_analysis/quality/data_quality.py` | 品質判定ロジック | quality report | `conf/data/quality/base.yaml` | 品質判定変更 |
| `src/tabular_analysis/reporting/report.py` | 単体レポート生成 | report.md/json | `conf/leaderboard/*` | レポート形式変更 |
| `src/tabular_analysis/reporting/pipeline_report.py` | pipelineレポート | report_* | `docs/24_REPORTING.md` | レポート要件変更 |
| `src/tabular_analysis/io/schema.py` | スキーマ推定 | schema.json | pandas | 入力形式追加 |
| `src/tabular_analysis/io/bundle_io.py` | モデル/前処理バンドル | bundle保存/読込 | joblib | bundle仕様変更 |
| `src/tabular_analysis/uncertainty/conformal.py` | 予測区間 | conformal interval | `conf/eval/base.yaml` | 予測不確実性変更 |
| `src/tabular_analysis/viz/data_profile.py` | データプロファイル | Plotly | `conf/viz/base.yaml` | 可視化拡張 |
| `src/tabular_analysis/viz/plots.py` | 汎用プロット | Plotly | `conf/viz/base.yaml` | 図の追加/変更 |
| `src/tabular_analysis/viz/regression_plots.py` | 回帰向け図 | scatter/residuals | `conf/viz/base.yaml` | 回帰可視化変更 |
| `src/tabular_analysis/viz/leaderboard_plots.py` | leaderboard図 | table/bar | `conf/leaderboard/scoring.yaml` | 比較図変更 |
| `src/tabular_analysis/viz/infer_plots.py` | 推論可視化 | input-output table | `conf/task/infer/base.yaml` | 推論図変更 |
| `src/tabular_analysis/viz/optuna_plots.py` | 最適化可視化 | Optuna図 | optuna | 最適化図変更 |
| `src/tabular_analysis/serve/app.py` | 推論API | HTTP | `serving/settings.py` | API拡張 |
| `src/tabular_analysis/serve/model_loader.py` | モデルロード | model_id | SPDML/ローカル | モデル配布変更 |
| `src/tabular_analysis/serve/settings.py` | API設定 | env/config | settings | API運用変更 |
| `src/tabular_analysis/serve/auth.py` | API認証 | token/auth | settings | 認証方式変更 |

### 2.2 `conf/` 配下
| ファイル/ディレクトリ | 役割 | 主な入出力 | 関連設定/依存 | 変更が必要になりやすいケース |
| --- | --- | --- | --- | --- |
| `conf/config.yaml` | Hydra defaults | 実行全体のデフォルト | すべて | デフォルト運用変更 |
| `conf/run/base.yaml` | 実行/ SPDML設定 | run.* | SPDML運用 | 実行モード切替 |
| `conf/run/alerts/base.yaml` | アラート設定 | run.alerts.* | ops/alerting | 通知経路変更 |
| `conf/data/base.yaml` | データ設定 | data.* | dataset_register/preprocess | 入力形式変更 |
| `conf/data/quality/base.yaml` | 品質ゲート | data.quality.* | ops/data_quality | 品質基準変更 |
| `conf/eval/base.yaml` | 評価設定 | eval.* | train/leaderboard | 評価指標変更 |
| `conf/ensemble/base.yaml` | アンサンブル設定 | ensemble.* | train_ensemble | アンサンブル方式変更 |
| `conf/leaderboard/scoring.yaml` | スコアリング設定 | scoring.* | leaderboard | 推奨ルール変更 |
| `conf/exec_policy/base.yaml` | 実行制限/queue | exec_policy.* | pipeline | 実行制御変更 |
| `conf/monitor/base.yaml` | ドリフト監視 | monitor.* | infer/drift | 監視指標変更 |
| `conf/viz/base.yaml` | 可視化設定 | viz.* | ui_logger | 図のON/OFF |
| `conf/task/*/base.yaml` | タスク別設定 | task.* / preprocess/train/infer | 各process | タスク挙動変更 |
| `conf/group/model/*.yaml` | モデルバリアント | model_variant.* | registry/models | モデル追加 |
| `conf/group/preprocess/*.yaml` | 前処理バリアント | preprocess_variant.* | registry/preprocessors | 前処理追加 |
| `conf/group/split/*.yaml` | splitバリアント | split_variant.* | preprocess | split戦略追加 |
| `conf/group/infer_mode/*.yaml` | 推論モード | infer_mode.* | infer | 推論方式追加 |
| `conf/pipeline/model_sets/*.yaml` | モデルセット | pipeline.model_set | pipeline | モデルセット変更 |
| `conf/clearml/*` | SPDML UI/テンプレ | project_layout/templates/hparams | SPDML運用 | UI規約変更 |
| `conf/ops/*` | 運用ポリシー | usecase_id/processed_dataset | ops/* | 命名・保存方針変更 |

### 2.3 その他（`tools/`, `serving/` など）
| ファイル/ディレクトリ | 役割 | 主な入出力 | 関連設定/依存 | 変更が必要になりやすいケース |
| --- | --- | --- | --- | --- |
| `tools/clearml_entrypoint.py` | SPDML task 実行入口 | Hydra overrides | SPDML Agent | Agent実行運用変更 |
| `tools/rehearsal/*` | リハーサル/検証 | 実行ログ/検証結果 | docs/67 | 運用検証手順変更 |
| `tools/tests/*` | 自動検証 | SPDML UI検証 | docs/15 | 検証要件変更 |
| `serving/*` | 推論API | HTTP API | serving設定 | Servingの導入/変更 |

## 3. コード処理ワークフロー（Mermaid）
```mermaid
flowchart TD
  A[dataset_register] --> B[preprocess]
  B --> C1[train_model (model variants)]
  B --> C2[train_model (model variants)]
  C1 --> D[train_ensemble (optional)]
  C2 --> D
  C1 --> E[leaderboard]
  C2 --> E
  D --> E
  E --> F[infer (single/batch/optimize)]
  P[pipeline] -. orchestrate .-> B
  P -. orchestrate .-> C1
  P -. orchestrate .-> D
  P -. orchestrate .-> E
  P -. orchestrate .-> F
```

## 4. 除外対象の整理
以下は Codex CLI 用の指示/作業ファイルであり、本コード仕様の説明から除外します。
- `work/`（Codex task 指示）
- `APPLY_TASKS_*.md` / `plan2.md` / Agent関連メモ類
- `tools/codex_loop/`（Codex 自動実行スクリプト）
- `docs/issues/`（課題管理テンプレ）
