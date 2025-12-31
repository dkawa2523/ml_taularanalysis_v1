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

## Adapter で接続した API パス（T003 現状）
- ClearML Task 初期化: `ml_platform.integrations.clearml.task_factory`
- properties/tags: `ml_platform.integrations.clearml.set_user_properties`
- Artifacts upload: `ml_platform.integrations.clearml.upload_artifact`
- config_resolved.yaml: `ml_platform.config.export_config_artifact`（artifact_name="config_resolved.yaml"）
- manifest.json: `ml_platform.artifacts.write_manifest`
- hashes: `ml_platform.artifacts.hash_config` / `hash_split` / `hash_recipe`
- versioning: `ml_platform.versioning.get_code_version` / `get_platform_version` / `get_schema_version`

## Notes (T004)
- ClearML Dataset registration is not implemented in ml_platform yet.
- Solution adapter uses `clearml.Dataset` directly for dataset_register (candidate for platform uplift).

## 期待する入力/出力（adapter の挙動）
- `init_task_context(cfg, stage, task_name, tags, properties)` → `TaskContext`
  - ClearML 無効: task=None の context を返す
  - ClearML 有効: task を初期化して返す（API が見つからない場合は例外）
  - tags: `usecase:<usecase_id>` / `process:<process>` / `schema:<schema_version>` / `grid:<grid_run_id>` を自動付与
  - properties: `usecase_id`, `process`, `schema_version`, `code_version`, `platform_version`, `grid_run_id` を自動付与
- `save_config_resolved(ctx, cfg)` → `config_resolved.yaml` の保存 + ClearML へ artifact 登録
- `write_out_json(ctx, out)` → `out.json` の保存 + ClearML へ artifact 登録
- `write_manifest(ctx, manifest)` → `manifest.json` の保存 + ClearML へ artifact 登録
  - 必須キー: `schema_version`, `code_version`, `platform_version`, `inputs`, `outputs`, `hashes`
  - `hashes` 必須キー: `config_hash`, `split_hash`, `recipe_hash`

## 実装手順（Codex タスク T003）
- `ml_platform` を import し、P201〜P204 で追加された関数の実体を探す
- `platform_adapter.py` の candidates を更新し、正しい関数へ接続する
- platform 側に機能が足りない場合：まず Solution 内で代替実装し、
  2 Solution 以上で共通になった段階で platform への昇格（plan2）
