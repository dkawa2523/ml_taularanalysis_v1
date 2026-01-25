# T060 ClearML契約のリハーサル手順を更新（Datasets/Plots/Controllerが期待通りか検証する）

## Objective
processed dataset / plots&scalars / pipeline controller / templates を試験段階で確実に検証できる手順書とコマンドを docs に整備する。

## Risk / Redundancy check (read before coding)
- 変更は **ClearML統合の薄い層**（`src/tabular_analysis/clearml/`）へ集約し、process側に重複ロジックを散らさない。
- HyperParameters/Configuration は **最小**。全文connect禁止（UIがノイズで死ぬ）。
- local pipeline と pipeline_controller の仕様二重化を避ける（plan/step定義を共通化）。

## Context / Why
試験段階は運用固定をしない一方で、仕様検証は抜け漏れなく行う必要がある。再現可能な手順がないと社内サーバー移行で詰まる。

## Instructions (do exactly)
1. `docs/42_REHEARSAL_SCENARIOS.md` を更新し、以下を追加:
   - processed dataset が Datasets に作られる確認（SDKで Dataset.get）
   - train の Scalars/Plots/Debug Samples の確認
   - pipeline_controller 実行手順（agent起動含む）
   - template 作成 → controller 実行 → 子タスク生成確認
2. `docs/53_CLEARML_HYPERPARAMETERS_CONTRACT.md` と整合させる（UIで何を見るべきか）
3. UIチェックリストを `docs/55_CLEARML_UI_CHECKLIST.md` として追加（任意だが推奨）


## Acceptance Criteria
- docs/ に、ローカルClearMLでの検証手順（コマンド付き）が一箇所にまとまっている。
- 新機能の確認項目（Datasets/Plots/Scalars/Controller/Templates/HyperParameters）が明確で、実施できる。


## Verification (run locally)
```bash
python -m compileall -q src
python - <<'PY'
from pathlib import Path
req = [
 'docs/50_CLEARML_PROCESSED_DATASET_CONTRACT.md',
 'docs/51_CLEARML_PLOTS_SCALARS_DEBUGSAMPLES_CONTRACT.md',
 'docs/52_CLEARML_PIPELINE_CONTROLLER_CONTRACT.md',
 'docs/53_CLEARML_HYPERPARAMETERS_CONTRACT.md',
 'docs/54_CLEARML_MINIMALITY_GUIDE.md',
]
for p in req:
    assert Path(p).exists(), p
print('docs ok')
PY

```

## Result
- RESULT: TODO (nonce: <fill>)
