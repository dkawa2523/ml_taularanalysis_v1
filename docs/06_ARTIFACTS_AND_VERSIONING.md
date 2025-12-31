# 06_ARTIFACTS_AND_VERSIONING（追跡性とバージョニング）

## 必須 Artifacts（全タスク）
- `config_resolved.yaml`：Hydra の最終合成設定
- `out.json`：そのタスクの構造化出力（後工程が参照）
- `manifest.json`：追跡性（inputs/outputs/hashes/version）

これらは P201〜P204 で追加された ml-platform のユーティリティ（hash/manifest/out writer）を利用して生成します。
Solution 側は `platform_adapter.py` 経由で呼び出します。

## manifest.json（例）
```json
{
  "schema_version": "v1",
  "created_at": "2025-12-31T12:00:00Z",
  "code_version": "<git sha>",
  "platform_version": "<ml_platform version>",
  "process": "train_model",
  "inputs": {
    "processed_dataset_id": "...",
    "split_hash": "..."
  },
  "outputs": {
    "model_id": "..."
  },
  "hashes": {
    "config_hash": "...",
    "split_hash": "...",
    "recipe_hash": "..."
  }
}
```

## hash のルール（推奨）
- `config_hash`：解決済み config の正規化（順序安定）
- `split_hash`：train/val の index（または seed+strategy+group/time 列など）の正規化
- `recipe_hash`：前処理 recipe の正規化

## version の取り扱い
- Solution は `run.schema_version` を固定（v1）
- Platform は SemVer で運用し、Solution は pin（plan2 A 案）
