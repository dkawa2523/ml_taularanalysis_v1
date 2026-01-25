# T057 Scalars/Plots/Debug Samples を UI 契約通りに出す（png artifact偏重を改善）

## Objective
重要指標を Scalars、可視化を Plotly で Plots、サンプルを Debug Samples に出し、Artifacts は再現用ファイル中心に整理する。

## Risk / Redundancy check (read before coding)
- 変更は **ClearML統合の薄い層**（`src/tabular_analysis/clearml/`）へ集約し、process側に重複ロジックを散らさない。
- HyperParameters/Configuration は **最小**。全文connect禁止（UIがノイズで死ぬ）。
- local pipeline と pipeline_controller の仕様二重化を避ける（plan/step定義を共通化）。

## Context / Why
現状はpng等がArtifactsに埋もれてUIの検索性/理解が落ちる。ClearMLの強み（Scalars/Plots/Debug Samples/HyperParameters）を活かし、非DSがUIだけで判断できる状態に近づける。

## Instructions (do exactly)
1. `src/tabular_analysis/clearml/ui_logger.py` を新設し、UI出力を集約:
   - `log_scalar(task, title, series, value, step=0)`
   - `log_plotly(task, title, series, fig, step=0)`（plotly無い場合のfallbackも実装）
   - `log_debug_text(task, title, series, text, step=0)`
   - `log_debug_table(task, title, series, df, step=0)`（可能なら）
2. `src/tabular_analysis/clearml/hparams.py` の connect を各タスクで呼ぶ（タスクの“再現に必要な最小”のみ）
3. train_model:
   - primary_metric を Scalars `metrics/<primary_metric>` に出す
   - 可能なら Plotly 図を Plots に出す（重要度/ROC/Confusion/Residual）
   - 先頭サンプルの予測（数行）を Debug Samples（text/table）に出す
4. leaderboard:
   - best_score を scalar（leaderboard/best_score）
   - top-k bar を plotly
5. infer:
   - 入力/出力サンプルを Debug Samples
   - 任意で latency を scalar
6. Artifact:
   - 既存の `manifest/out/config` は維持
   - png は“UIで必要なら”Plotsに載せる。Artifactsへのpng残しは必須ではない。
7. docs/51, docs/53 を更新


## Acceptance Criteria
- train task の Scalars に primary_metric が表示される。
- train task の Plots に少なくとも 1つの Plotly 図が表示される（環境によりfallback可）。
- infer task に Debug Samples（入力/出力サンプル）が表示される。
- 各タスクの HyperParameters に必要最小の設定が載る（docs/53準拠）。


## Verification (run locally)
```bash
python -m compileall -q src
python tools/tests/smoke_plots.py
# UI確認（ローカルClearML）: Scalars/Plots/Debug Samplesに出ていること

```

## Result
- RESULT: preprocess に Debug Samples（raw_sample / processed_sample）を追加し、UIで入力/出力の例を確認可能にした。
- RESULT: train_ensemble に optional scalar `ensemble/best_score` を追加し、UIで指標が追えるようにした。
