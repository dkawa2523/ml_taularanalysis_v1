# 再現性・成果物・バージョニング

## 必須成果物（全タスク）
- `config_resolved.yaml`：Hydra の最終設定
- `out.json`：構造化出力（後工程が参照）
- `manifest.json`：inputs/outputs/hash/version の追跡情報

## hash / version
- `config_hash` / `split_hash` / `recipe_hash` を manifest に記録
- `run.schema_version` は v1 固定
- platform のバージョンは `platform_version` に記録

詳細は `docs/06_ARTIFACTS_AND_VERSIONING.md` を参照。
