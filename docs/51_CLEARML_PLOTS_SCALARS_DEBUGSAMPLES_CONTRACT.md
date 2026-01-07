# ClearML: Plots / Scalars / Debug Samples 契約 v2

## 目的
- 画像や数値が Artifact に埋もれる問題を解消する。
- 非DSが ClearML UI の **Scalars / Plots / Debug Samples** を見れば判断できるようにする。
- Artifact は「再現・追跡用のファイル（json/csv/bundle）」中心にする。

## 設計（冗長化を防ぐ）
- ClearML UI 出力は `tabular_analysis/clearml/ui_logger.py` に集約し、各 process が個別に logger API を乱用しない。
- **png を生成して artifact に置くだけ**は NG。UI に載せたい図は `report_plotly` / `report_image` で Plots に表示する。

## 1. Scalars（必須）
Train task:
- `metrics/<primary_metric>`（例: roc_auc, rmse）
- `metrics/secondary/<...>`（必要な範囲で）
Leaderboard task:
- `leaderboard/best_score`
Infer task:
- `infer/latency_ms`（推奨）
Pipeline(orchestrator) task:
- `pipeline/num_models`, `pipeline/num_succeeded`, `pipeline/num_failed`

## 2. Plots（必須）
Train task（最低限）:
- feature importance（bar）
- confusion matrix（classification）
- roc curve（binary classification）
- residual plot（regression）

Leaderboard task:
- top-k bar（スコア）

実装方針:
- `task.get_logger().report_plotly(...)` を優先
- plotly が導入されていない環境も想定し、fallback を用意:
  - plotly が無ければ `report_image` で png を Plots に出す

## 3. Debug Samples（推奨）
- 入力・出力例（小さなサンプル）を `report_text` / `report_table` / `report_image` で残す
- 例:
  - preprocess: raw sample / processed sample の先頭数行
  - train_model: 予測サンプル（y_true/y_pred の数行）
  - infer: 入力レコード / 出力レコードの例

## 4. Artifacts に残す（継続）
- `manifest.json`, `out.json`, `config_resolved.yaml`（必須）
- `leaderboard.csv`, `recommendation.json`（必要）
- png は原則 artifacts で必須ではない（Plots で代替）
