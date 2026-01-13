"""Registry (plugins).

- models
- preprocessors
- metrics
- variants (pipeline v2 defaults)

Codex タスクで拡張します。
"""

from .variants import (  # noqa: F401
    ApplicabilityResult,
    SchemaSummary,
    VariantSpec,
    list_default_ensemble_methods,
    list_default_model_variants,
    list_default_preprocess_variants,
    list_ensemble_methods,
    list_model_variants,
    list_preprocess_variants,
    missing_dependencies,
)

__all__ = [
    "ApplicabilityResult",
    "SchemaSummary",
    "VariantSpec",
    "list_default_ensemble_methods",
    "list_default_model_variants",
    "list_default_preprocess_variants",
    "list_ensemble_methods",
    "list_model_variants",
    "list_preprocess_variants",
    "missing_dependencies",
]
