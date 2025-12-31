"""Schema utilities.

T005 で実装予定。
- 入力データの型/列情報を抽出し schema.json として保存
- infer 時に schema を使って入力検証する
"""

from __future__ import annotations

from typing import Any, Dict


def infer_schema(df) -> Dict[str, Any]:
    raise NotImplementedError
