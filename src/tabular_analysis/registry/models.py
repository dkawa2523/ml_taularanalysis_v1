"""Model registry.

T006 で実装予定。
- conf/group/model/*.yaml の class_path/framework/params を読み、実体を生成する
"""

from __future__ import annotations

from typing import Any, Dict


def build_model(model_variant: Dict[str, Any]):
    raise NotImplementedError("build_model is not implemented yet")
