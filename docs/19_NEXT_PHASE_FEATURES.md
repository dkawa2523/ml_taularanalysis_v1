# 次フェーズ機能（T029〜T040）概要

このドキュメントは、T028完了後に追加した「高度なテーブル解析機能」を **業務運用（ClearML UI）に支障が出ない形**で運用するための設計メモです。

## 基本方針
- **デフォルトOFF**: 追加機能は yaml で明示的に opt-in する（ノイズ抑制）
- **比較可能性（comparability）最優先**: split/metric/target_type 等が一致するものだけを leaderboard 比較対象にする
- **成果物は増やしすぎない**: 追加出力は「必要な1〜3ファイル」に絞り、summary.md から辿れるようにする
- **platform改修を要求しない**: platform_adapter 経由で利用し、足りないものは solution 側で完結（共通化が見えたら別途 platform 昇格）

## 追加済みの機能カテゴリ（T029〜T039）
- 分類拡張: 多クラス・不均衡（PR-AUC / class_weight 等）
- 特徴量: 高カーディナリティカテゴリ（hashing / frequency / OOFターゲットエンコーディング）
  - preprocess で `preprocess.categorical.encoding` を切替し、report で列ごとの次元数を追跡
- 不確かさ: 回帰の予測区間（conformal split）
- 評価の堅牢化: ブートストラップCI
- 意思決定支援: model card / decision summary
- ガバナンス: champion-challenger（promote/rollback）
- 監視: drift の強化（train profile ↔ infer profile）
- スケール: chunked batch infer
- 任意: Serving API skeleton（fastapiはoptional）

## 検証導線
- quick: `python tools/tests/verify_all.py --quick`（主要スモーク + 多クラス + 高カーディナリティ）
- full: `python tools/tests/verify_all.py --full`（不確かさ / 指標CI / 監視 / ガバナンス / スケール / Serving）
- 詳細は `docs/15_VERIFICATION.md` を参照

## ClearML上のノイズ制御（推奨）
- タスク種別は増やさない（既存 process に “追加オプション” として組み込む）
- Properties は **少数の固定キー**に寄せる（例: `task_type`, `n_classes`, `imbalance`, `calibration`, `uncertainty`）
- Artifacts は “契約3点” + 追加は必要最小限
  - 例: `model_card.md`, `decision_summary.md`, `decision_summary.json`, `metrics_ci.json`, `drift_report.json`, `drift_report.md`
