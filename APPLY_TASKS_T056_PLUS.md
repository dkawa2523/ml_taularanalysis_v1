# APPLY: T056〜T060（v2）Codexタスク追加

## 目的
ClearML の想定仕様（processed dataset管理 / Plots&Scalars / PipelineController / HyperParameters）に合わせるための改修タスク（T056〜T060）を追加します。

## 重要（冗長化防止）
- ClearML API を直接触る実装は `src/tabular_analysis/clearml/` に集約してください。
- HyperParameters は「再現に必要な最小」だけを connect（docs/53）。全文connectはしません。
- local pipeline と controller pipeline の仕様二重化を避ける（plan共通化）。

## 適用
1) ZIP を workspace 直下で unzip（ml-solution-tabular-analysis を上書き追加）
2) 追記ファイルを queue にマージ

```bash
cd <workspace>/ml-solution-tabular-analysis
python tools/codex_loop/merge_queue_additions.py --queue work/queue.json --add work/queue_additions_T056_T060.json
```

## 実行
```bash
python tools/codex_loop/run.py --repo . --once
python tools/codex_loop/run.py --repo .
```

## ローカルClearMLでの検証（目安）
- processed dataset が Datasets に作成される（Dataset.getで取得できる）
- train の Scalars/Plots/Debug Samples に情報が出る
- pipeline_controller で子タスクが作成される（agent起動が必要）
- HyperParameters に必要最小の設定が載る（docs/53）
