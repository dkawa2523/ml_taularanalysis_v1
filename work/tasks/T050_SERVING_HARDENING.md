# T050 Serving Hardening（認証・ステージ選択・監査ログ・入力検証）

## Objective
- T040 の serving 雛形を “業務投入に耐える最低限” まで強化する
  - 認証（API key など簡易）
  - production/staging など stage 指定でモデルを選べる
  - 推論入力のスキーマ検証（strict/warn/coerce）
  - 監査ログ（JSONL）でいつ誰が何を投げたか追える
- 依存増で開発が律速しないよう、serving は optional（extras）を維持し、コア解析には影響しない

---

## Scope
### 1) serving 設定
- `serving/settings.py` を追加（環境変数で設定）
  - `API_KEY`
  - `MODEL_STAGE` / `MODEL_REF`
  - `AUDIT_LOG_PATH`
  - `SCHEMA_MODE`（strict/warn/coerce）

### 2) 認証
- `X-API-Key` ヘッダで簡易認証（無設定なら無効、または必須にするかを設定で選べる）
- 認証失敗時は 401

### 3) モデルロード戦略
- stage 指定（production/staging）でモデルを選択
  - ClearML 有効：Model Registry を参照（adapter 経由）
  - ClearML 無効：ローカルの `model_registry_state.json` または `MODEL_REF` で指定
- 予測は既存の `model_bundle` を利用し、training と同じ前処理が必ず通る

### 4) 入力検証 + 監査ログ
- schema の必須列/型を検証（mode で挙動を変える）
- 監査ログは JSONL（timestamp, request_id, model_ref, status, latency_ms, error_summary）

### 5) docs と verify_all
- `docs/29_SERVING.md` を更新し、起動・設定・運用上の注意を記載
- `tools/tests/test_serving_app.py` を追加（依存が無い場合は skip でOK）

---

## Acceptance Criteria
- `python -c "from serving.app import app; print(app)"` が成功する（依存があれば）
- テストで /health と /predict が呼べる（TestClient）
- 認証/監査ログ/スキーマ検証の挙動が確認できる
- 依存が無い環境でも verify が通る（テストが skip になる）

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_serving_app.py
python tools/tests/verify_all.py --quick
```
