# 29_SERVING (Hardening)

This document describes the hardened serving options added in T050. Serving remains
optional and is only activated when the FastAPI extras are installed.

## Install optional dependencies

```bash
pip install -e ".[api]"
```

## Run with uvicorn

```bash
export MODEL_STAGE=production
export API_KEY=your-key
export SCHEMA_MODE=warn
export AUDIT_LOG_PATH=./audit.jsonl
uvicorn serving.app:app --reload
```

## Environment variables

- `API_KEY`
  - Optional. If set, `X-API-Key` header is required.
  - Comma-separated values are accepted for key rotation.
- `MODEL_REF`
  - Explicit model reference. Supports a `model_bundle.joblib` path or a run directory
    containing `model_bundle.joblib`.
- `MODEL_STAGE`
  - Stage selector (`production`, `staging`, `archived`).
  - When ClearML credentials/config are present, the registry is queried via the adapter.
  - When ClearML is not configured, a local `model_registry_state.json` is used.
- `SCHEMA_MODE`
  - `strict`: reject inputs with schema errors (HTTP 422).
  - `warn`: allow inputs with schema issues (warnings in response).
  - `coerce`: attempt dtype coercion and continue (warnings in response).
- `AUDIT_LOG_PATH`
  - JSONL audit log path. Each request appends one line.

Optional helpers:
- `USECASE_ID`: select a usecase when `model_registry_state.json` has multiple entries.
- `MODEL_REGISTRY_STATE_PATH`: explicit path to `model_registry_state.json` (defaults to CWD).

## Endpoints

`GET /health`
- Returns status, model reference, and configuration hints.

`POST /predict`
- Accepts a single record, list of records, or wrapped payload:
  `{"records": [...]}` / `{"inputs": [...]}`.

Example:

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"records":[{"num1":1.2,"num2":3.4,"cat":"a"}]}'
```

## Audit log

When `AUDIT_LOG_PATH` is set, each request appends one JSON line containing:
- `timestamp`, `request_id`, `model_ref`, `status`, `latency_ms`, `error_summary`

Additional fields include status codes, schema mode, and row counts.

## Notes

- If both `MODEL_REF` and `MODEL_STAGE` are unset, serving reports a load error.
- `MODEL_STAGE` follows ClearML registry tags: `stage:<stage>` (and `usecase:<id>` when provided).
- The same preprocessing pipeline from training is always applied via `model_bundle.joblib`.
