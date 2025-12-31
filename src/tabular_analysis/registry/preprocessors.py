"""Preprocessor registry.

T005 で実装予定。
- numeric/categorical 列の推定
- 欠損補完 + スケーリング + エンコーディング
- transformer を bundle 化して保存
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from pandas.api.types import is_bool_dtype, is_numeric_dtype


def infer_feature_types(df, feature_columns: Iterable[str]) -> Tuple[List[str], List[str]]:
    numeric: List[str] = []
    categorical: List[str] = []
    for col in feature_columns:
        series = df[col]
        if is_bool_dtype(series):
            categorical.append(col)
        elif is_numeric_dtype(series):
            numeric.append(col)
        else:
            categorical.append(col)
    return numeric, categorical


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def build_preprocessor(
    preprocess_variant: Dict[str, Any],
    *,
    numeric_features: List[str],
    categorical_features: List[str],
    numeric_impute: str,
    categorical_impute: str,
):
    from sklearn.compose import ColumnTransformer  # type: ignore
    from sklearn.impute import SimpleImputer  # type: ignore
    from sklearn.pipeline import Pipeline  # type: ignore
    from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, OrdinalEncoder, StandardScaler  # type: ignore

    if not numeric_features and not categorical_features:
        raise ValueError("No feature columns available for preprocessing.")

    numeric_scaler = _normalize_text(preprocess_variant.get("numeric_scaler", "standard"))
    categorical_encoder = _normalize_text(preprocess_variant.get("categorical_encoder", "onehot"))
    handle_unknown = preprocess_variant.get("handle_unknown", "ignore")

    numeric_steps = [("imputer", SimpleImputer(strategy=str(numeric_impute)))]
    if numeric_scaler in ("", "none", "passthrough"):
        pass
    elif numeric_scaler in ("standard", "std", "stdscaler"):
        numeric_steps.append(("scaler", StandardScaler()))
    elif numeric_scaler in ("minmax", "min_max", "minmaxscaler"):
        numeric_steps.append(("scaler", MinMaxScaler()))
    else:
        raise ValueError(f"Unsupported numeric_scaler: {numeric_scaler}")

    categorical_steps = [("imputer", SimpleImputer(strategy=str(categorical_impute)))]
    if categorical_encoder in ("", "none", "passthrough"):
        pass
    elif categorical_encoder in ("onehot", "ohe"):
        categorical_steps.append(
            (
                "encoder",
                OneHotEncoder(handle_unknown=str(handle_unknown), sparse_output=False),
            )
        )
    elif categorical_encoder in ("ordinal", "ordinal_encoder"):
        categorical_steps.append(
            (
                "encoder",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
            )
        )
    else:
        raise ValueError(f"Unsupported categorical_encoder: {categorical_encoder}")

    transformers = []
    if numeric_features:
        transformers.append(("num", Pipeline(steps=numeric_steps), list(numeric_features)))
    if categorical_features:
        transformers.append(("cat", Pipeline(steps=categorical_steps), list(categorical_features)))

    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=True,
    )
