"""Variant/step registry for pipeline v2 defaults."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import importlib.util
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..io.schema import extract_schema_dtypes

_OPTIONAL_FRAMEWORKS = {"lightgbm", "xgboost", "catboost", "tabpfn"}

_PREPROCESS_REGISTRY = [
    {"id": "stdscaler_ohe", "default_enabled": True},
]

_MODEL_REGISTRY = [
    {"id": "linear_regression", "default_enabled": True},
    {"id": "ridge", "default_enabled": True},
    {"id": "random_forest", "default_enabled": True},
    {"id": "gradient_boosting", "default_enabled": True},
    {"id": "logistic_regression", "default_enabled": True},
    {"id": "lasso", "default_enabled": False},
    {"id": "elasticnet", "default_enabled": False},
    {"id": "extra_trees", "default_enabled": False},
    {"id": "knn", "default_enabled": False},
    {"id": "svr", "default_enabled": False},
    {"id": "svc", "default_enabled": False},
    {"id": "gaussian_process", "default_enabled": False},
    {"id": "mlp", "default_enabled": False},
    {"id": "lgbm", "default_enabled": False},
    {"id": "xgboost", "default_enabled": False},
    {"id": "catboost", "default_enabled": False},
    {"id": "tabpfn", "default_enabled": False},
]

_ENSEMBLE_REGISTRY = [
    {"id": "mean_topk", "default_enabled": True},
    {"id": "weighted", "default_enabled": False},
    {"id": "stacking", "default_enabled": False},
]

_CLASS_PATH_TASK_TYPE_OVERRIDES = {
    "sklearn.linear_model.LogisticRegression": "classification",
    "sklearn.linear_model.ElasticNet": "regression",
    "sklearn.linear_model.Lasso": "regression",
}


@dataclass(frozen=True)
class ApplicabilityResult:
    ok: bool
    reason: str | None = None

    @classmethod
    def success(cls) -> "ApplicabilityResult":
        return cls(ok=True, reason=None)

    @classmethod
    def skip(cls, reason: str) -> "ApplicabilityResult":
        return cls(ok=False, reason=reason)


@dataclass(frozen=True)
class SchemaSummary:
    numeric_columns: tuple[str, ...]
    categorical_columns: tuple[str, ...]
    has_schema: bool = True

    @property
    def has_numeric(self) -> bool:
        return bool(self.numeric_columns)

    @property
    def has_categorical(self) -> bool:
        return bool(self.categorical_columns)


ApplicabilityCheck = Callable[[Mapping[str, Any] | SchemaSummary | None], ApplicabilityResult]


@dataclass(frozen=True)
class VariantSpec:
    id: str
    group: str
    default_enabled: bool
    supports: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    applicability_check: ApplicabilityCheck | None = None

    def supports_task_type(self, task_type: str | None) -> bool:
        if not task_type or not self.supports:
            return True
        normalized = _normalize_task_type(task_type)
        return normalized in self.supports

    def check_applicability(self, schema: Mapping[str, Any] | SchemaSummary | None) -> ApplicabilityResult:
        if self.applicability_check is None:
            return ApplicabilityResult.success()
        return self.applicability_check(schema)

    def missing_dependencies(self) -> list[str]:
        return missing_dependencies(self.requires)


def missing_dependencies(requires: Sequence[str]) -> list[str]:
    missing: list[str] = []
    for module in requires:
        name = _normalize_text(module)
        if not name:
            continue
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    return missing


def summarize_schema(schema: Mapping[str, Any] | SchemaSummary | None) -> SchemaSummary:
    if isinstance(schema, SchemaSummary):
        return schema
    if not isinstance(schema, Mapping):
        return SchemaSummary((), (), has_schema=False)
    dtypes = extract_schema_dtypes(schema)
    if not dtypes:
        return SchemaSummary((), (), has_schema=True)
    numeric: list[str] = []
    categorical: list[str] = []
    for name, dtype in dtypes.items():
        dtype_key = _normalize_text(dtype)
        if _is_bool_dtype(dtype_key):
            categorical.append(str(name))
        elif _is_numeric_dtype(dtype_key):
            numeric.append(str(name))
        else:
            categorical.append(str(name))
    return SchemaSummary(tuple(numeric), tuple(categorical), has_schema=True)


def list_preprocess_variants(
    task_type: str | None = None,
    schema: Mapping[str, Any] | None = None,
    *,
    defaults_only: bool = False,
    filter_inapplicable: bool = True,
) -> list[VariantSpec]:
    specs = list(_preprocess_registry())
    specs = _filter_by_task_type(specs, task_type)
    specs = _filter_by_defaults(specs, defaults_only)
    if filter_inapplicable and schema is not None:
        specs = [spec for spec in specs if spec.check_applicability(schema).ok]
    return specs


def list_default_preprocess_variants(
    task_type: str | None = None,
    schema: Mapping[str, Any] | None = None,
    *,
    filter_inapplicable: bool = True,
) -> list[VariantSpec]:
    return list_preprocess_variants(
        task_type=task_type,
        schema=schema,
        defaults_only=True,
        filter_inapplicable=filter_inapplicable,
    )


def list_model_variants(
    task_type: str | None = None,
    *,
    defaults_only: bool = False,
) -> list[VariantSpec]:
    specs = list(_model_registry())
    specs = _filter_by_task_type(specs, task_type)
    specs = _filter_by_defaults(specs, defaults_only)
    return specs


def list_default_model_variants(task_type: str | None = None) -> list[VariantSpec]:
    return list_model_variants(task_type=task_type, defaults_only=True)


def list_ensemble_methods(
    task_type: str | None = None,
    *,
    defaults_only: bool = False,
) -> list[VariantSpec]:
    specs = list(_ensemble_registry())
    specs = _filter_by_task_type(specs, task_type)
    specs = _filter_by_defaults(specs, defaults_only)
    return specs


def list_default_ensemble_methods(task_type: str | None = None) -> list[VariantSpec]:
    return list_ensemble_methods(task_type=task_type, defaults_only=True)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _normalize_task_type(value: Any) -> str:
    key = _normalize_text(value)
    if key in ("classification", "classifier", "class", "multiclass", "multi_class", "multi-class"):
        return "classification"
    if key in ("regression", "regressor", "reg"):
        return "regression"
    return "regression"


def _normalize_task_types(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, (list, tuple, set)):
        items = values
    else:
        items = [values]
    normalized: set[str] = set()
    for item in items:
        key = _normalize_text(item)
        if not key:
            continue
        normalized.add(_normalize_task_type(key))
    return normalized


def _is_numeric_dtype(dtype_key: str) -> bool:
    return dtype_key.startswith(
        (
            "int",
            "uint",
            "float",
            "double",
            "decimal",
            "number",
        )
    )


def _is_bool_dtype(dtype_key: str) -> bool:
    return dtype_key in ("bool", "boolean") or dtype_key.startswith("bool")


def _supports_tuple(values: set[str]) -> tuple[str, ...]:
    order = ("regression", "classification")
    ordered = [item for item in order if item in values]
    if not ordered:
        ordered = sorted(values)
    return tuple(ordered)


def _filter_by_task_type(specs: list[VariantSpec], task_type: str | None) -> list[VariantSpec]:
    if not task_type:
        return specs
    return [spec for spec in specs if spec.supports_task_type(task_type)]


def _filter_by_defaults(specs: list[VariantSpec], defaults_only: bool) -> list[VariantSpec]:
    if not defaults_only:
        return specs
    return [spec for spec in specs if spec.default_enabled]


def _to_container(value: Any) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        return OmegaConf.to_container(value, resolve=True)
    return value


def _task_types_from_class_path(class_path: Any) -> set[str]:
    class_path = _to_container(class_path)
    if isinstance(class_path, Mapping):
        return {t for t in (_normalize_task_type(key) for key in class_path.keys()) if t}
    if isinstance(class_path, str):
        override = _CLASS_PATH_TASK_TYPE_OVERRIDES.get(class_path)
        if override:
            return {_normalize_task_type(override)}
        if "Classifier" in class_path:
            return {"classification"}
        if "Regressor" in class_path or "Regression" in class_path:
            return {"regression"}
    return set()


def _resolve_model_supports(model_variant: Mapping[str, Any]) -> set[str]:
    explicit = _normalize_task_types(model_variant.get("task_type"))
    if explicit:
        return explicit
    class_types = _task_types_from_class_path(model_variant.get("class_path"))
    if class_types:
        return class_types
    return set()


def _make_preprocess_applicability(
    *,
    variant_id: str,
    numeric_scaler: str,
    categorical_encoder: str,
) -> ApplicabilityCheck:
    numeric_required = numeric_scaler not in ("", "none", "passthrough")
    categorical_required = categorical_encoder not in ("", "none", "passthrough")

    def _check(schema: Mapping[str, Any] | SchemaSummary | None) -> ApplicabilityResult:
        summary = summarize_schema(schema)
        if not summary.has_schema:
            return ApplicabilityResult.success()
        if numeric_required and not summary.has_numeric:
            return ApplicabilityResult.skip(
                f"{variant_id} requires numeric columns for numeric_scaler={numeric_scaler}"
            )
        if categorical_required and not summary.has_categorical:
            return ApplicabilityResult.skip(
                f"{variant_id} requires categorical columns for categorical_encoder={categorical_encoder}"
            )
        return ApplicabilityResult.success()

    return _check


def _resolve_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    return Path.cwd()


def _load_yaml(path: Path) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception as exc:
        raise RuntimeError("OmegaConf is required to load registry configs.") from exc
    try:
        cfg = OmegaConf.load(path)
    except Exception as exc:
        raise ValueError(f"Failed to load registry config: {path}") from exc
    return OmegaConf.to_container(cfg, resolve=False)


@lru_cache(maxsize=None)
def _load_group_variant(group: str, variant_id: str, key: str) -> Mapping[str, Any]:
    root = _resolve_repo_root()
    path = root / "conf" / "group" / group / f"{variant_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Missing config for {group} variant: {path}")
    payload = _load_yaml(path)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Registry config must be a mapping: {path}")
    variant = payload.get(key)
    if not isinstance(variant, Mapping):
        raise ValueError(f"{key} section is missing: {path}")
    name = _normalize_text(variant.get("name")) or variant_id
    if name != variant_id:
        raise ValueError(f"{key}.name must match '{variant_id}': {path}")
    return variant


@lru_cache(maxsize=None)
def _preprocess_registry() -> tuple[VariantSpec, ...]:
    specs: list[VariantSpec] = []
    for entry in _PREPROCESS_REGISTRY:
        variant_id = str(entry["id"])
        variant = _load_group_variant("preprocess", variant_id, "preprocess_variant")
        numeric_scaler = _normalize_text(variant.get("numeric_scaler", "standard"))
        categorical_encoder = _normalize_text(variant.get("categorical_encoder", "onehot"))
        specs.append(
            VariantSpec(
                id=variant_id,
                group="preprocess",
                default_enabled=bool(entry.get("default_enabled", False)),
                supports=("regression", "classification"),
                requires=tuple(entry.get("requires", []) or ()),
                applicability_check=_make_preprocess_applicability(
                    variant_id=variant_id,
                    numeric_scaler=numeric_scaler,
                    categorical_encoder=categorical_encoder,
                ),
            )
        )
    return tuple(specs)


@lru_cache(maxsize=None)
def _model_registry() -> tuple[VariantSpec, ...]:
    specs: list[VariantSpec] = []
    for entry in _MODEL_REGISTRY:
        variant_id = str(entry["id"])
        variant = _load_group_variant("model", variant_id, "model_variant")
        supports = entry.get("supports")
        if supports:
            supports_set = _normalize_task_types(supports)
        else:
            supports_set = _resolve_model_supports(variant)
        requires = list(entry.get("requires", []) or [])
        if not requires:
            framework = _normalize_text(variant.get("framework"))
            if framework in _OPTIONAL_FRAMEWORKS:
                requires = [framework]
        specs.append(
            VariantSpec(
                id=variant_id,
                group="train",
                default_enabled=bool(entry.get("default_enabled", False)),
                supports=_supports_tuple(supports_set),
                requires=tuple(requires),
            )
        )
    return tuple(specs)


@lru_cache(maxsize=None)
def _ensemble_registry() -> tuple[VariantSpec, ...]:
    specs: list[VariantSpec] = []
    for entry in _ENSEMBLE_REGISTRY:
        specs.append(
            VariantSpec(
                id=str(entry["id"]),
                group="ensemble",
                default_enabled=bool(entry.get("default_enabled", False)),
                supports=("regression", "classification"),
                requires=tuple(entry.get("requires", []) or ()),
            )
        )
    return tuple(specs)
