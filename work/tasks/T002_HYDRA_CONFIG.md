# T002 Hydra 設計: タスク単位 config + バリアント設計

## Objective
- `conf/` の設計を「独立タスク運用」に耐える形に整える
- タスクごとに ClearML Project/Stage が固定され、`pipeline` からも安全に呼べる構造にする

## Context
- split の責務：preprocess
- pipeline は接着剤（重い処理は持たない）

## Instructions
1. `conf/config.yaml` の defaults を整理し、以下を満たす
   - デフォルト task は `pipeline`
   - `task=<name>` で切り替え可能
   - `group/model=...` `group/preprocess=...` などバリアント指定が CLI でできる

2. `conf/task/*/base.yaml` を見直し、全タスク共通で次を満たす
   - `task.name`, `task.stage`, `task.project_name` を持つ
   - stage 名は docs/03 の Project 階層と対応

3. `conf/group/*/*.yaml` を「registry が解釈しやすい形」に整える
   - model: `model_variant.name/framework/class_path/params`
   - preprocess: `preprocess_variant.name/...`

4. docs 反映
   - `docs/05_PROCESS_CATALOG.md` の I/O 記述に config key を合わせる

## Acceptance Criteria
- `python -m tabular_analysis.cli --print-config task=preprocess` が成功
- `python -m tabular_analysis.cli --print-config task=train_model` が成功
- docs/05 の記述と config のキーが一致している

## Verification
```bash
python -m tabular_analysis.cli --print-config task=preprocess > /dev/null
python -m tabular_analysis.cli --print-config task=train_model > /dev/null
```
