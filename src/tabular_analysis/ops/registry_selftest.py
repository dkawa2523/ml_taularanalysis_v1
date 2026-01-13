"""Self-test for variant registry applicability and dependency checks."""

from __future__ import annotations

import argparse
from typing import Any

from ..registry import list_preprocess_variants, missing_dependencies


def _toy_schema(*, numeric: bool, categorical: bool) -> dict[str, Any]:
    fields: dict[str, dict[str, Any]] = {}
    if numeric:
        fields["num_feature"] = {"dtype": "float64"}
    if categorical:
        fields["cat_feature"] = {"dtype": "object"}
    return {"fields": fields}


def _find_spec(specs, variant_id: str):
    for spec in specs:
        if spec.id == variant_id:
            return spec
    raise RuntimeError(f"Variant '{variant_id}' not found in registry.")


def run_selftest() -> None:
    specs = list_preprocess_variants(filter_inapplicable=False)
    std_spec = _find_spec(specs, "stdscaler_ohe")

    ok = std_spec.check_applicability(_toy_schema(numeric=True, categorical=True))
    if not ok.ok:
        raise AssertionError(f"stdscaler_ohe should be applicable: {ok.reason}")

    no_cat = std_spec.check_applicability(_toy_schema(numeric=True, categorical=False))
    if no_cat.ok:
        raise AssertionError("stdscaler_ohe should skip when categorical columns are missing.")

    no_num = std_spec.check_applicability(_toy_schema(numeric=False, categorical=True))
    if no_num.ok:
        raise AssertionError("stdscaler_ohe should skip when numeric columns are missing.")

    missing = missing_dependencies(["__tabular_analysis_missing_dep__"])
    if "__tabular_analysis_missing_dep__" not in missing:
        raise AssertionError("missing_dependencies did not flag the dummy module.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run registry self-test checks.")
    parser.parse_args()
    run_selftest()
    print("registry selftest: ok")


if __name__ == "__main__":
    main()
