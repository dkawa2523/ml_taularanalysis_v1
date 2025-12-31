"""Schema utilities.

T005 で実装予定。
- 入力データの型/列情報を抽出し schema.json として保存
- infer 時に schema を使って入力検証する
"""

from __future__ import annotations

from typing import Any, Dict


def infer_schema(df) -> Dict[str, Any]:
    rows = int(df.shape[0])
    cols = int(df.shape[1])
    null_count = df.isna().sum()
    fields: Dict[str, Any] = {}
    for col in df.columns:
        key = str(col)
        count = int(null_count[col])
        rate = float(count / rows) if rows else 0.0
        fields[key] = {
            "dtype": str(df[col].dtype),
            "null_count": count,
            "null_rate": rate,
        }
    return {"rows": rows, "columns": cols, "fields": fields}
