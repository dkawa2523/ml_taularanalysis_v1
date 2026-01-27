# SPDML共通仕様

## 1. SPDML管理対象
| 管理対象 | 内容 | 主な更新元 | 参照先 |
| --- | --- | --- | --- |
| Task | dataset_register/preprocess/train/ensemble/leaderboard/infer/pipeline | `src/tabular_analysis/processes/*` | UI/比較 |
| Dataset | raw / processed dataset | `src/tabular_analysis/clearml/datasets.py` | 学習/推論 |
| Model | 学習済みモデル登録 | `platform_adapter.register_model_artifact` | 推論/配布 |
| Artifacts | config/out/manifest/plots/report | `platform_adapter` | 追跡性 |
| Plots/Scalars | 指標・図表 | `clearml/ui_logger.py` | UI確認 |

## 2. タスク項目一覧
| タスク項目 | 内容 | 用途 | 設定/生成箇所 |
| --- | --- | --- | --- |
| Tags | `usecase:*`, `process:*`, `schema:*`, `grid:*` など | 検索/比較 | `platform_adapter` + `docs/66_*` |
| Properties | usecase_id/process/schema_version等 | 追跡性 | `platform_adapter` |
| HyperParameters | 再実行に必要な最小キー | UI確認 | `conf/clearml/hyperparams_sections.yaml` |
| Artifacts | `config_resolved.yaml` / `out.json` / `manifest.json` | 再現性 | `platform_adapter` |
| Plots/Scalars | 指標/表/図 | 可視化 | `clearml/ui_logger.py` |

## 3. 共通仕様の運用効率化
| 機能 | タスク種類 | 共通仕様 | 運用効率化のポイント |
| --- | --- | --- | --- |
| タグ/命名 | 全タスク | `docs/66_*`に準拠 | 探索キーが統一される |
| HyperParams | 全タスク | section分割 | UIが読みやすい |
| Artifacts | 全タスク | config/out/manifest必須 | 再実行/監査が容易 |
| Project階層 | 全タスク | `conf/clearml/project_layout.yaml` | usecase単位で整理 |
| Template運用 | controller/agent | `conf/clearml/templates.yaml` | 本番運用の再現性 |
