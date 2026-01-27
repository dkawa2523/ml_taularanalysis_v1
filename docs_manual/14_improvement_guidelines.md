# 改良方法ガイドライン

## 1. 変更ポイント一覧（テーブル）
| 改良項目 | 対象ファイル/ディレクトリ | 変更内容の要点 | 関連する設定 | 影響範囲 |
| --- | --- | --- | --- | --- |
| 前処理追加 | `conf/group/preprocess/*.yaml`, `src/tabular_analysis/registry/preprocessors.py` | 新バリアント追加 | `preprocess.variant` | preprocess/train/infer |
| モデル追加 | `conf/group/model/*.yaml`, `src/tabular_analysis/registry/models.py` | class_path/params追加 | `train.model` | train/leaderboard |
| アンサンブル追加 | `conf/ensemble/base.yaml`, `src/tabular_analysis/processes/train_ensemble.py` | method追加 | `ensemble.method` | train_ensemble/leaderboard |
| 評価指標追加 | `src/tabular_analysis/registry/metrics.py`, `conf/eval/base.yaml` | metric実装+登録 | `eval.metrics.*` | train/leaderboard |
| Leaderboard改善 | `src/tabular_analysis/processes/leaderboard.py`, `conf/leaderboard/scoring.yaml` | scoring/推薦変更 | `scoring.*` | leaderboard/report |
| 可視化追加 | `src/tabular_analysis/viz/*`, `conf/viz/base.yaml` | 新Plot追加 | `viz.*` | UI/レポート |
| SPDML UI | `src/tabular_analysis/clearml/*`, `conf/clearml/*` | タグ/階層/テンプレ | `run.clearml.*` | UI表示/運用 |
| 推論拡張 | `src/tabular_analysis/processes/infer.py`, `conf/task/infer/base.yaml` | mode追加/改善 | `infer.*` | infer |
| pipeline強化 | `src/tabular_analysis/processes/pipeline.py`, `conf/task/pipeline/base.yaml` | plan/driver変更 | `pipeline.*` | 全体フロー |

## 2. 前処理の改良
- `conf/group/preprocess/<id>.yaml` を追加し `preprocess_variant.name` を一致させる。
- `src/tabular_analysis/registry/preprocessors.py` に対応実装を追加。
- 高カーディナリティ対応は `feature_engineering/categorical.py` を利用。

## 3. 学習モデルの改良
- `conf/group/model/<id>.yaml` に class_path/params を追加。
- optional依存は `registry/models.py` の OPTIONAL_DEPENDENCIES を確認。
- 追加後は `pipeline.model_set` の範囲に入れるか検討。

## 4. アンサンブルの改良
- `conf/ensemble/base.yaml` に新方式を追加。
- `train_ensemble.py` に合成ロジックを実装。
- leaderboard の比較基準は維持する。

## 5. 可視化 Plot の改良
- `viz/*.py` に新Plotを追加し `clearml/ui_logger.py` から呼び出す。
- 重い可視化は `conf/viz/base.yaml` のフラグでON/OFF可能にする。

## 6. SPDML 連携の改良
- タグ/Properties: `src/tabular_analysis/ops/clearml_identity.py`
- HyperParams: `conf/clearml/hyperparams_sections.yaml` + `clearml/hparams.py`
- テンプレ: `conf/clearml/templates.yaml`

## 7. 検証・テスト
- `python tools/rehearsal/run_pipeline_v2.py --execution logging` で基本動作確認。
- UI検証: `python tools/tests/rehearsal_verify_clearml_ui.py --usecase-id <USECASE_ID>`
