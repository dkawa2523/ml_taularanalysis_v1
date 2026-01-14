# T082 ClearML の Scalars / Plots / Artifacts の役割を整理し、yamlで出力ON/OFF可能にする

## 背景（課題）
- 現状、画像や指標が Artifacts に寄っており、ClearML の Plots/Scalars が空に近い
- ただし情報量を増やしすぎると UI が冗長になり運用できない
- 開発者が後から “出力を増減” できるように、yaml で簡単に ON/OFF したい

---

## 目的
- **Scalars**: 重要指標（R2, RMSE, MAE など）を “検索・比較しやすい形” で記録
- **Plots**: 考察に必要なグラフ/テーブル（Plotly優先）を表示
- **Artifacts**: 詳細レポートや大きいファイル（決定サマリー、モデル詳細json、加工済みデータのmanifestなど）
- 出力の粒度は `conf/` で制御できる（True/False）

---

## 実装方針
### 1) ClearML reporting の薄いラッパを追加
例: `src/tabular_analysis/clearml/reporting.py`

- `report_scalar(task, title, series, value, iteration=0)`
- `report_plotly(task, title, series, fig, iteration=0)`
- `report_table(task, title, series, table_plotly_or_df, iteration=0)`
- ON/OFF は `cfg.run.clearml.reporting.*`（例: `enable_scalars`, `enable_plots`, `enable_tables`）で制御
- Plotly が無い場合は matplotlib fallback（画像として report_image）

### 2) タスク別の “最小セット” を定義（増やしすぎない）
#### preprocess
- Plots:
  - 欠損率（列ごと bar）
  - target 分布（回帰: hist、分類: bar）
- Artifacts:
  - `preprocess_manifest.json`（元raw_ds_id、variant、列情報、行数、split情報）

#### train_model
- Scalars:
  - primary_metric（例: r2）
  - rmse/mae/mse など（task_type に応じて）
- Plots:
  - y_true vs y_pred scatter（回帰）
  - confusion matrix / roc（分類、実装できる範囲で）
  - metrics table（Plotly table）
- Artifacts:
  - model bundle / training report json

#### leaderboard
- Plots:
  - ランキング table（model×preprocess）
  - primary_metric の bar chart
- Scalars（任意）:
  - best_score（primary_metric）
- Artifacts:
  - decision_summary.md / json（推薦理由・比較）

#### infer
- Plots:
  - 入力→出力のテーブル（ユーザー要望: DEBUG SAMPLES ではなく PLOTS に table 表示）
  - 予測分布（hist）
- Scalars:
  - 推論対象件数、必要なら aggregate 指標（true がある場合）
- Artifacts:
  - 推論出力（csv/parquet） + manifest

### 3) 実装位置は “可視化専用ディレクトリ” に寄せる
- `src/tabular_analysis/viz/`（または `visualization/`）にグラフ生成関数を置く
- process 本体は `viz.*` を呼ぶだけにする（processが肥大化しないように）

---

## 受け入れ基準（Acceptance Criteria）
- 主要タスクで Plots / Scalars が UI に表示される（Artifacts に偏らない）
- `conf/` のフラグで、Plots/Scalars を抑制できる（冗長性対策）
- `python -m compileall -q src` が通る

---

## テスト
- `python -m compileall -q src`
- （ClearML接続あり）toy データで preprocess/train/leaderboard を実行して UI を確認

---

## Update (2026-01-13)
- `run.clearml.reporting.*` のトグルが未実装で、Scalars/Plots/Debug Samples の抑制ができない
- refactor plan の Phase 1 (T101) で実装対象
- `run.clearml.reporting` を conf/run/base.yaml に追加し、ui_logger で enable_scalars/plots/tables を反映
