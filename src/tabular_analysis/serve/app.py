"""Serving API skeleton (FastAPI optional)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .auth import resolve_principal, verify_api_key
from .model_loader import resolve_model_bundle
from .settings import ServingSettings
from ..io.bundle_io import load_bundle
from ..processes import infer as infer_process


@dataclass(frozen=True)
class _ModelContext:
    bundle: dict[str, Any]
    model_bundle_path: Path
    preprocess_bundle: dict[str, Any]
    pipeline: Any
    model: Any
    calibrated_model: Any | None
    predictor: Any
    task_type: str
    n_classes: int | None
    class_labels: list[Any] | None
    label_encoder: Any | None
    threshold_used: float | None


def _require_fastapi():
    try:
        from fastapi import Body, FastAPI, HTTPException, Request, Response
    except Exception as exc:
        raise RuntimeError("FastAPI is required. Install with `pip install -e \".[api]\"`.") from exc
    return Body, FastAPI, HTTPException, Request, Response


def _load_context(bundle_path: Path) -> _ModelContext:
    bundle = load_bundle(bundle_path)
    if not isinstance(bundle, dict):
        raise ValueError("model_bundle.joblib is invalid.")
    model = bundle.get("model")
    preprocess_bundle = bundle.get("preprocess_bundle") or {}
    if model is None or not isinstance(preprocess_bundle, dict):
        raise ValueError("model_bundle is missing model or preprocess_bundle.")
    pipeline = preprocess_bundle.get("pipeline")
    if pipeline is None:
        raise ValueError("preprocess_bundle.pipeline is missing.")
    calibrated_model = bundle.get("calibrated_model")
    predictor = calibrated_model if calibrated_model is not None else model
    task_type = infer_process._normalize_task_type(bundle.get("task_type"))
    n_classes = bundle.get("n_classes")
    try:
        n_classes = int(n_classes) if n_classes is not None else None
    except Exception:
        n_classes = None
    class_labels = infer_process._resolve_class_labels(bundle, model)
    label_encoder = bundle.get("label_encoder")
    threshold_used = infer_process._resolve_threshold_used(bundle, n_classes=n_classes)
    return _ModelContext(
        bundle=bundle,
        model_bundle_path=bundle_path,
        preprocess_bundle=preprocess_bundle,
        pipeline=pipeline,
        model=model,
        calibrated_model=calibrated_model,
        predictor=predictor,
        task_type=task_type,
        n_classes=n_classes,
        class_labels=class_labels,
        label_encoder=label_encoder,
        threshold_used=threshold_used,
    )


def _extract_records(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        for key in ("records", "inputs", "data"):
            if key in payload:
                return payload[key]
    return payload


def _build_schema_payload(validation: Mapping[str, Any], *, mode: str) -> dict[str, Any]:
    issues = validation.get("issues") or {}
    return {
        "mode": mode,
        "ok": bool(validation.get("ok")),
        "warnings_count": int(validation.get("warnings_count") or 0),
        "errors_count": int(validation.get("errors_count") or 0),
        "issues": {
            "missing_columns": list(issues.get("missing_columns") or []),
            "extra_columns": list(issues.get("extra_columns") or []),
            "dtype_mismatch": list(issues.get("dtype_mismatch") or []),
            "coerce_failures": list(issues.get("coerce_failures") or []),
        },
    }


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_request_id(request: Any | None) -> str:
    if request is not None:
        try:
            headers = request.headers
        except Exception:
            headers = None
        if headers:
            for key in ("x-request-id", "x-correlation-id"):
                value = headers.get(key)
                if value:
                    return str(value)
    return uuid.uuid4().hex


def _summarize_error(detail: Any) -> str:
    if isinstance(detail, Mapping):
        for key in ("error", "message", "detail"):
            if key in detail:
                return str(detail[key])
    return str(detail)


def _write_audit_log(path: Path | None, payload: Mapping[str, Any]) -> None:
    if path is None:
        return
    try:
        audit_path = path.expanduser()
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=True)
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        return


def _predict_classification(ctx: _ModelContext, transformed: Any) -> list[dict[str, Any]]:
    if not hasattr(ctx.predictor, "predict_proba"):
        raise ValueError("classification inference requires predict_proba on the model.")

    proba = ctx.predictor.predict_proba(transformed)
    threshold_used = ctx.threshold_used
    if threshold_used is not None:
        positive_proba = infer_process._extract_positive_proba(proba)
        preds = (positive_proba >= threshold_used).astype(int)
    else:
        preds = ctx.predictor.predict(transformed)

    if ctx.label_encoder is not None and hasattr(ctx.label_encoder, "inverse_transform"):
        pred_labels = ctx.label_encoder.inverse_transform(preds)
    else:
        pred_labels = preds
        if ctx.class_labels:
            try:
                pred_labels = [ctx.class_labels[int(idx)] for idx in preds]
            except Exception:
                pred_labels = preds

    if hasattr(pred_labels, "tolist"):
        pred_labels = pred_labels.tolist()
    if not isinstance(pred_labels, list):
        pred_labels = list(pred_labels)

    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for classification probabilities.") from exc

    proba_arr = np.asarray(proba)
    if proba_arr.ndim == 1:
        proba_arr = np.stack([1.0 - proba_arr, proba_arr], axis=1)

    class_labels = ctx.class_labels
    if class_labels is None or len(class_labels) != int(proba_arr.shape[1]):
        class_labels = [str(i) for i in range(int(proba_arr.shape[1]))]

    predictions: list[dict[str, Any]] = []
    for idx, label in enumerate(pred_labels):
        payload = {
            "prediction": infer_process._sanitize_json_value(label),
            "predicted_label": infer_process._sanitize_json_value(label),
            "predicted_proba": infer_process._build_proba_payload(
                proba_arr[idx], class_labels
            ),
        }
        if threshold_used is not None:
            payload["threshold_used"] = infer_process._sanitize_json_value(threshold_used)
        predictions.append(payload)
    return predictions


def _predict_regression(ctx: _ModelContext, transformed: Any) -> list[dict[str, Any]]:
    preds = ctx.model.predict(transformed)
    rows = infer_process._preds_to_rows(preds)
    payloads: list[dict[str, Any]] = []
    for row in rows:
        if len(row) == 1:
            payload = {"prediction": infer_process._sanitize_json_value(row[0])}
        else:
            payload = {"prediction": [infer_process._sanitize_json_value(v) for v in row]}
        payloads.append(payload)
    return payloads


def create_app(model_bundle_path: str | None = None, *, strict_schema: bool | None = None) -> Any:
    Body, FastAPI, HTTPException, Request, Response = _require_fastapi()

    app = FastAPI(title="Tabular Analysis Serving API", version="0.1.0")

    settings = ServingSettings.from_env()
    if model_bundle_path:
        settings = settings.with_overrides(model_ref=model_bundle_path)
    if strict_schema is not None:
        settings = settings.with_overrides(
            schema_mode="strict" if strict_schema else "coerce"
        )

    resolution = resolve_model_bundle(settings)
    context: _ModelContext | None = None
    load_error: str | None = resolution.error

    if resolution.model_bundle_path is not None:
        try:
            context = _load_context(resolution.model_bundle_path)
        except Exception as exc:
            load_error = f"Failed to load model_bundle: {exc}"

    model_ref = resolution.model_ref
    if model_ref is None and resolution.model_bundle_path is not None:
        model_ref = str(resolution.model_bundle_path)

    validation_mode = settings.schema_mode

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok" if context is not None else "error",
            "model_bundle_path": str(resolution.model_bundle_path)
            if resolution.model_bundle_path is not None
            else None,
            "model_ref": model_ref,
            "model_stage": resolution.stage,
            "model_source": resolution.source,
            "schema_mode": validation_mode,
            "auth_enabled": settings.auth_required,
            "error": load_error,
        }

    @app.post("/predict")
    def predict(
        payload: Any = Body(...),
        request: Request | None = None,
        response: Response | None = None,
    ) -> dict[str, Any]:
        start = time.monotonic()
        request_id = _resolve_request_id(request)
        api_key = None
        if request is not None:
            api_key = request.headers.get("X-API-Key")
        principal = resolve_principal(api_key, settings.api_keys)
        status_code = 200
        error_summary: str | None = None
        schema_payload: dict[str, Any] | None = None
        n_rows: int | None = None

        try:
            if settings.auth_required and not verify_api_key(api_key, settings.api_keys):
                status_code = 401
                error_summary = "unauthorized"
                raise HTTPException(status_code=401, detail={"error": "Unauthorized"})

            if context is None:
                status_code = 503
                error_summary = _summarize_error(load_error or "Model is not loaded")
                raise HTTPException(status_code=503, detail={"error": load_error})

            records = _extract_records(payload)
            df = infer_process._frame_from_payload(records)

            df, validation = infer_process._validate_inputs(
                df,
                context.preprocess_bundle,
                validation_mode=validation_mode,
            )
            schema_payload = _build_schema_payload(validation, mode=validation_mode)

            if validation_mode == "strict" and not schema_payload["ok"]:
                status_code = 422
                error_summary = "schema_validation_failed"
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "Input schema validation failed.",
                        "schema_validation": schema_payload,
                    },
                )

            transformed = context.pipeline.transform(df)

            if context.task_type == "classification":
                predictions = _predict_classification(context, transformed)
            else:
                predictions = _predict_regression(context, transformed)

            n_rows = len(predictions)
            if response is not None:
                try:
                    response.headers["X-Request-Id"] = request_id
                except Exception:
                    pass

            return {
                "task_type": context.task_type,
                "predictions": predictions,
                "schema_validation": schema_payload,
                "n_rows": n_rows,
                "request_id": request_id,
            }
        except HTTPException as exc:
            status_code = exc.status_code
            if error_summary is None:
                error_summary = _summarize_error(exc.detail)
            raise
        except Exception as exc:
            status_code = 500
            error_summary = str(exc)
            raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc
        finally:
            latency_ms = int((time.monotonic() - start) * 1000)
            _write_audit_log(
                settings.audit_log_path,
                {
                    "timestamp": _timestamp(),
                    "request_id": request_id,
                    "model_ref": model_ref,
                    "model_stage": resolution.stage,
                    "status": "ok" if status_code < 400 else "error",
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "error_summary": error_summary,
                    "principal": principal,
                    "schema_mode": validation_mode,
                    "schema_ok": schema_payload.get("ok") if schema_payload else None,
                    "n_rows": n_rows,
                },
            )

    return app


def _build_default_app() -> Any | None:
    try:
        return create_app()
    except RuntimeError:
        return None


app = _build_default_app()
