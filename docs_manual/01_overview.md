# 概要

## 1. 想定背景
- 表形式（CSV/Parquet）の業務データを対象に、学習・比較・推論を**再現性のある手順**で運用したい。
- 非DSユーザーでも SPDML 上で**結果比較・判断・再実行**ができる運用を目指す。
- 複数モデル/前処理の組み合わせが増え、**比較可能性・追跡性・運用統一**が課題化している。

## 2. 課題
- 前処理/学習/推論の結果が散逸し、**どの設定で作った成果か追跡しづらい**。
- split 再生成や設定混入により、**モデル比較の公平性が崩れる**。
- SPDML上の表示やタグ/Propertiesが揃わず、**非DSが判断しにくい**。
- optional dependency や実行モード（local/logging/agent）差で**再現性が崩れる**。
- 学習結果をもとに**推論・最適化・運用判断**まで一貫した流れがない。

## 3. 本コードの概要
- **タブular向けの前処理・学習・評価・推論**を独立タスクとして提供。
- `dataset_register → preprocess → train_model → (train_ensemble) → leaderboard → infer` の流れを**pipeline**が統一的にオーケストレーション。
- すべてのタスクで `config_resolved.yaml / out.json / manifest.json` を出力し、**追跡性を必須化**。
- SPDML 連携により、**タスク/データセット/モデルの見え方を統一**。

## 4. 本コードの機能一覧
- **データセット登録**: rawデータの登録・スキーマ推定・プロファイル可視化
- **前処理**: 欠損補完、スケーリング、カテゴリエンコード、split固定
- **学習**: 回帰/分類モデルの学習、CV、評価指標計算
- **自動アンサンブル**: mean_topk / weighted / stacking
- **Leaderboard**: 比較可能性チェック、複合スコアで推奨
- **推論**: single / batch / optimize（Optuna）
- **ドリフト/品質ゲート**: データ品質チェック、ドリフト検知
- **レポーティング**: report.md/report.json/report_links.json
- **運用**: local / logging / agent / pipeline_controller の実行モード

## 5. 課題への有用性
| 課題 | 本コードの対応 | 効果 |
| --- | --- | --- |
| 比較可能性が崩れる | preprocess が split を固定し、leaderboard が comparability を判定 | 公平なモデル比較が可能 |
| 追跡性が弱い | 全タスクで manifest/out.json を出力 | 再現・監査が容易 |
| SPDML UI が読みにくい | タグ/Properties/HyperParams セクションを標準化 | 非DSでも判断可能 |
| 実行モード差異 | local/logging/agent/pipeline_controller を統一仕様で扱う | 運用移行が容易 |
| 推論/最適化までの運用 | single/batch/optimize の推論機能 | 施策最適化が可能 |
