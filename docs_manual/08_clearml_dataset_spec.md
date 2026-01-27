# SPDMLへのデータセット仕様

## 1. 配置/プロジェクト階層
- `run.clearml.project_root / run.clearml.project_layout.solution_root / run.usecase_id / group_map.dataset_register` に登録。
- processed dataset は preprocessのプロジェクト階層に登録。

## 2. 登録されるファイル内容
| ファイル | 内容 | 生成元 | 参照用途 |
| --- | --- | --- | --- |
| `schema.json` | 列/型/欠損率 | dataset_register/preprocess | 入力確認 |
| `preview.csv` | 先頭サンプル | dataset_register | UI確認 |
| `splits.json` | train/valid/test index | preprocess | 再現性 |
| `recipe.json` | 前処理レシピ | preprocess | 検証/追跡 |
| `preprocess_bundle.joblib` | 前処理transformer | preprocess | 推論時変換 |
| `meta.json` | hash/rows/features | preprocess | 比較可能性 |
| `X.parquet` | 特徴量 | preprocess | 学習入力（store_features=true） |
| `y.parquet` | 目的変数 | preprocess | 学習入力（store_features=true） |

## 3. SPDML タブ項目ごとの付加情報
| タブ | 付加情報 | 生成/更新タイミング | 備考 |
| --- | --- | --- | --- |
| Files | 上記ファイル群 | dataset_register/preprocess | store_featuresで増減 |
| Artifacts | config/out/manifest | 全タスク | 追跡性必須 |
| Plots | データ分布/欠損率 | dataset_register/preprocess | UI確認 |
| Scalars | rows/columns/missing_rate | dataset_register | 監視補助 |

## 4. データセット重複への対応
- dataset名に `usecase_id/preprocess_variant/split_hash/schema_version` を含める。
- 同一条件は version で区別し、latestを参照可能。

## 5. その他の工夫
- `ops.processed_dataset.store_features=false` で巨大データの保存を抑制。
- `recipe_hash` / `split_hash` で比較可能性を担保。
