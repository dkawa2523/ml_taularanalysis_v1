# Serving / API

## 位置づけ
- `serving/` は FastAPI の起動入口（`serving.app:app`）
- 実体は `src/tabular_analysis/serve/` 配下
- 依存は optional（`pip install -e ".[api]"`）

## エンドポイント
- `GET /health`：稼働/モデル参照状態を返す
- `POST /predict`：単一レコード / 複数レコードに対応（`records` / `inputs` / 生配列）

## 認証
- `API_KEY` 環境変数が設定されている場合のみ `X-API-Key` が必須
- 未設定なら匿名アクセス

## モデル参照の優先順位
1. `MODEL_REF`（または `TABULAR_MODEL_BUNDLE*`）で直接指定
2. `MODEL_STAGE` + ClearML Registry（設定があれば）
3. `MODEL_STAGE` + `model_registry_state.json`（ローカル）

## 主な環境変数
- `MODEL_REF`: 明示的な `model_bundle.joblib` パス（ディレクトリ指定も可）
- `MODEL_STAGE`: `production` / `staging` / `archived`
- `SCHEMA_MODE`: `strict` / `warn` / `coerce`
- `AUDIT_LOG_PATH`: JSONL 監査ログ出力先

詳細は `docs/22_SERVING.md` と `docs/29_SERVING.md` を参照。
