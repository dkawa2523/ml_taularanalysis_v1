# 13_PLATFORM_INTEGRATION（ml-platform 連携）

本 Solution は `dkawa2523/ml_platform_v1` の P201〜P204 反映済み状態を前提にします。

## 前提にする platform 機能（要求）
1. ClearML タスクの初期化を標準化するユーティリティ
   - project_name / task_name / tags / properties の統一
   - execution モード（local/logging/agent/clone）の吸収
2. Artifacts の標準出力
   - `config_resolved.yaml`
   - `out.json`
   - `manifest.json`
3. hash / manifest の生成（追跡性）
   - config_hash, split_hash, recipe_hash（少なくとも config_hash）

## Solution 側の方針
- Solution は platform の API を直接 import しない
- `src/tabular_analysis/platform_adapter.py` だけが platform に依存する

## 実装手順（Codex タスク T003）
- `ml_platform` を import し、P201〜P204 で追加された関数の実体を探す
- `platform_adapter.py` の candidates を更新し、正しい関数へ接続する
- platform 側に機能が足りない場合：まず Solution 内で代替実装し、
  2 Solution 以上で共通になった段階で platform への昇格（plan2）
