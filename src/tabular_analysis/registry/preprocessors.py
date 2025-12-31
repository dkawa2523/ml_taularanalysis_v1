"""Preprocessor registry.

T005 で実装予定。
- numeric/categorical 列の推定
- 欠損補完 + スケーリング + エンコーディング
- transformer を bundle 化して保存
"""

from __future__ import annotations

from typing import Any, Dict


def build_preprocessor(preprocess_variant: Dict[str, Any]):
    raise NotImplementedError("build_preprocessor is not implemented yet")
