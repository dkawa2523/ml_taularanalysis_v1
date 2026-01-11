# T039 （任意）Serving: 推論APIスケルトン（FastAPI optional / base依存は増やさない）

## Objective
- 学習済み model_bundle を “業務システム” に組み込む導線として、推論APIのスケルトンを提供する
- ただし base 依存を増やさない（fastapi/uvicorn は **optional extras**）
- CI/verify は fastapi 未導入でも通るようにする（import guard / lazy import）

---

## Scope
### 1) 実装（solution側）
- `src/tabular_analysis/serve/app.py`（または同等）を追加
  - `create_app(model_bundle_path: str, strict_schema: bool=...)` のような factory を用意
  - `/health` と `/predict`（JSON入力→予測結果JSON）を実装
  - schema validation（T026）を再利用（coerce/strict）
- `src/tabular_analysis/serve/__init__.py` を追加

### 2) optional dependency
- `pyproject.toml` に optional extras を追加
  - `api = ["fastapi>=0.110", "uvicorn>=0.27"]`（目安）
- `docs/22_SERVING.md` に実行例
  - `pip install -e ".[api]"` → `uvicorn tabular_analysis.serve.app:app --reload`

### 3) tests（fastapi無しでも通す）
- `tools/tests/smoke_serve_import.py`
  - fastapi 未導入でも `import tabular_analysis.serve` が落ちないこと（lazy import を確認）
  - fastapi が入っている場合は簡単な起動テストは optional（skipでOK）

---

## Acceptance Criteria
- serving スケルトンが追加され、ドキュメントが整備される
- base の verify が fastapi 未導入でも通る
- `smoke_serve_import.py` が通る

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_serve_import.py`

---

## Notes / Risks
- ここは “あくまで雛形”。本番運用は認証・監査・スケーリング等が別途必要
- fastapi を base requirements に入れない（保守律速を避ける）

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加した optional extras:
- verify 結果:
