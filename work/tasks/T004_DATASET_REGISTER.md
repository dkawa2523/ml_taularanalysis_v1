# T004 dataset_register 実装: rawデータ登録 + schema + manifest/out

## Objective
- `dataset_register` を実装し、raw データの出自が追跡できる状態を作る
- ClearML 有効時は「Dataset として登録（または取得）」し、無効時はローカルハッシュで代替する

## Inputs
- `data.dataset_path`（CSV/Parquet）または `data.raw_dataset_id`

## Required Outputs
- `out.json`
  - `raw_dataset_id`（ClearML Dataset ID または local:<hash>）
  - `raw_schema`（列数/行数/dtypes/欠損率など）
  - `raw_dataset_hash`（ファイル hash）
- `manifest.json`（docs/06 の形式）

## Implementation Notes
- platform 連携（ClearML Dataset 登録）が platform 側で用意されている場合はそれを使う。無ければ Solution 側の最小実装でよいが、platform へ昇格候補として docs/13 にメモする。
- schema は軽量に：
  - 行数、列数
  - dtype（pandas の dtype 名）
  - 欠損率（null count / rows）
  - head(5) を preview.csv として artifact（任意）

## Acceptance Criteria
- local モードで `python -m tabular_analysis.cli task=dataset_register data.dataset_path=/path/to/file.csv` が例外なく終了し、outputs 配下に out.json/manifest.json/config_resolved.yaml が生成される
- ClearML 有効時（logging）に登録できる（接続は環境依存のため、実行は任意）

## Verification（最低限）
- このリポジトリにはデータを同梱しないため、検証は「一時ファイルを作って実行」する形式で実装してください。

例：
```bash
python - <<'PY'
import pandas as pd
from pathlib import Path
p = Path('tmp_dataset.csv')
import numpy as np
pd.DataFrame({'x':[1,2,3],'y':[10,11,12]}).to_csv(p, index=False)
print(p)
PY

python -m tabular_analysis.cli task=dataset_register data.dataset_path=tmp_dataset.csv run.clearml.enabled=false
```
