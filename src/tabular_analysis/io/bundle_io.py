"""Bundle IO.

T005/T006/T008 で実装予定。
- preprocess bundle / model bundle の保存・読み込み
- joblib などでの直列化
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def save_bundle(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import joblib  # type: ignore
    except Exception as exc:
        raise RuntimeError("joblib is required for bundle serialization.") from exc
    joblib.dump(obj, path)


def load_bundle(path: Path) -> Any:
    try:
        import joblib  # type: ignore
    except Exception as exc:
        raise RuntimeError("joblib is required for bundle serialization.") from exc
    return joblib.load(path)
