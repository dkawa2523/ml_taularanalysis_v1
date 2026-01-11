# ClearML 統合の最小性ガイド v1（設計が冗長にならないために）

## 目的
- ClearML 連携の実装が各 process に散らばり、将来の保守が難しくなるのを防ぐ。
- Solution（tabular-analysis）側で追加する ClearML ロジックを「薄い層」に閉じ込める。

## ルール
1) ClearML API を直接呼ぶのは原則 `src/tabular_analysis/clearml/` のみ
2) process は「何を記録するか」を宣言し、記録手段は clearml 層に委譲
3) UI は “Scalars/Plots/Debug Samples” を優先し、Artifacts は再現用ファイル中心
4) HyperParameters は「再現に必要な最小」に限定し、ノイズを増やさない
5) pipeline_controller は local pipeline と仕様を共有し、二重実装を避ける

## 推奨構造
- `tabular_analysis/clearml/datasets.py`（Dataset create/get）
- `tabular_analysis/clearml/hparams.py`（抽出 & connect）
- `tabular_analysis/clearml/ui_logger.py`（scalars/plots/debug）
- `tabular_analysis/clearml/templates.py`（template探索/検証）
- `tabular_analysis/clearml/pipeline_controller.py`（controller組み立て）
