# T005 preprocess 実装: 前処理 + split固定 + bundle

## Objective
- raw データから、学習に必要な「前処理 bundle」と「固定 split」を生成する
- 以降の train_model はこの split を再生成しない（docs/07）

## Inputs
- `data.raw_dataset_id` または `data.dataset_path`
- `data.target_column`, `data.id_columns`, `data.drop_columns`
- `data.split.*`
- `preprocess.variant`（conf/group/preprocess/*.yaml）

## Required Outputs
- `out.json`
  - `processed_dataset_id`（ClearML Dataset ID または local:<hash>）
  - `split_hash`
  - `recipe_hash`
  - `preprocess_variant`（名前）
- `manifest.json`
- 追加 Artifacts（最低限）
  - `schema.json`
  - `split.json`（train_index / val_index など）
  - `preprocess_bundle.joblib`（sklearn pipeline / column info）

## Implementation Notes
- 前処理の実装は `registry/preprocessors.py` に集約し、`conf/group/preprocess/*.yaml` を解釈して pipeline を組み立てる
- bundle の save/load は `io/bundle_io.py` に集約（joblib 推奨）
- `recipe_hash` は「前処理の定義（variant + 主要パラメータ + 入力列の一覧）」を正規化して hash
- `split_hash` は「train/val の index 配列」を正規化して hash（順序安定）

## Acceptance Criteria
- local モードで preprocess が完走し、outputs/02_preprocess/ に out.json/manifest.json/... が生成される
- split を再現可能（同じ入力と config なら split_hash が一致）

## Verification（例）
```bash
python - <<'PY'
import pandas as pd
from pathlib import Path
p = Path('tmp_dataset.csv')
pd.DataFrame({
  'id':[1,2,3,4,5,6],
  'x':[1.0,2.0,3.0,4.0,5.0,6.0],
  'cat':['a','b','a','b','a','b'],
  'y':[10,11,12,13,14,15],
}).to_csv(p, index=False)
print(p)
PY

python -m tabular_analysis.cli task=preprocess data.dataset_path=tmp_dataset.csv data.target_column=y run.clearml.enabled=false
```
